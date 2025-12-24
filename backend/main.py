from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import joblib
import pandas as pd

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

# ✅ Load ML model and label mappings
model = joblib.load("model/credit_model.pkl")
import json
with open("../ml/data/label_mappings.json", "r") as f:
    label_mappings = json.load(f)

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

# ✅ Prediction route
@app.post("/predict")
def predict_credit(data: CreditInput):
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
    prediction = model.predict(df)[0]
    probability = model.predict_proba(df)[0][1]  # prob of funded

    return {
        "funded_probability": float(probability),
        "prediction": "Funded" if prediction == 1 else "Not Funded",
        "recommendation": "Approve" if prediction == 1 else "Reject"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)