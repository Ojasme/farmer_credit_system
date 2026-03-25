from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import joblib
import pandas as pd
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env if present
load_dotenv()

# ✅ Create FastAPI app
app = FastAPI(title="Farmer Credit Scoring API")

# ✅ Enable CORS (needed for React)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Load ML model and label mappings (paths resolved relative to this file)
BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "model" / "credit_model.pkl"
model = joblib.load(MODEL_PATH)
import json
# Prefer label mappings saved alongside model (training script writes to backend/model), else fall back to ml/data
LABEL_PATH = BASE_DIR / "model" / "label_mappings.json"
if LABEL_PATH.exists():
    with open(LABEL_PATH, "r") as f:
        label_mappings = json.load(f)
else:
    with open(BASE_DIR / ".." / "ml" / "data" / "label_mappings.json", "r") as f:
        label_mappings = json.load(f)

# Load optimized threshold if available
threshold = 0.5
THRESH_PATH = BASE_DIR / "model" / "threshold.json"
if THRESH_PATH.exists():
    with open(THRESH_PATH, "r") as f:
        try:
            threshold = float(json.load(f).get("best_threshold", 0.5))
        except Exception:
            threshold = 0.5

# ✅ Request schema (accept strings for categorical)
class CreditInput(BaseModel):
    loan_amount: float
    term_in_months: float
    repayment_interval: str
    country: str
    activity: str
    region: str
    partner_id: str  # as string since encoded
    loan_theme_type: str
    mpi: float
    theme_loan_density: float
    num_female_borrowers: int
    num_male_borrowers: int
    posted_year: int
    posted_month: int

# ✅ Health check route
@app.get("/")
def root():
    return {"status": "Farmer Credit API running"}


from auth import send_otp_service, verify_otp_service, get_current_user

class SendOtpRequest(BaseModel):
    email: str

class VerifyOtpRequest(BaseModel):
    email: str
    otp: str

@app.post("/auth/send_otp")
def send_otp(req: SendOtpRequest):
    email = req.email.strip()
    return send_otp_service(email)

@app.post("/auth/verify_otp")
def verify_otp(req: VerifyOtpRequest):
    email = req.email.strip()
    otp = req.otp.strip()
    token = verify_otp_service(email, otp)
    return {"access_token": token, "token_type": "bearer"}

# Protect prediction endpoint using JWT dependency
from fastapi import Depends

@app.post("/predict")
def predict_credit(data: CreditInput, email: str = Depends(get_current_user)):
    # Prepare data
    input_data = data.dict()
    
    # Encode categorical using mappings
    for col in label_mappings:
        if col in input_data:
            value = input_data[col]
            if isinstance(value, str):
                input_data[col] = label_mappings[col].get(value, 0)  # fallback to 0 if unknown
            elif isinstance(value, (int, float)):
                input_data[col] = int(value)  # already encoded
    
    # partner_id is sent as str, convert to int
    input_data['partner_id'] = int(float(input_data['partner_id']))
    
    df = pd.DataFrame([input_data])
    probability = float(model.predict_proba(df)[0][1])  # prob of funded
    prediction_label = 1 if probability >= threshold else 0

    return {
        "funded_probability": probability,
        "prediction": "Funded" if prediction_label == 1 else "Not Funded",
        "recommendation": "Approve" if prediction_label == 1 else "Reject",
        "threshold_used": threshold
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)