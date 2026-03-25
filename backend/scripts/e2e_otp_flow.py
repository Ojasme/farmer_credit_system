#!/usr/bin/env python3
"""End-to-end OTP flow test using FastAPI TestClient (no external services required).
- Sends OTP via /auth/send_otp (dev fallback returns otp in response when Twilio not configured)
- Verifies via /auth/verify_otp
- Calls /predict with the returned JWT
"""
from pathlib import Path
import sys
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from fastapi.testclient import TestClient
import fakeredis

from main import app
import auth

# Use fake redis for isolation
fake = fakeredis.FakeRedis(decode_responses=True)
auth.redis_client = fake

client = TestClient(app)

EMAIL = "test@example.com"

print("Sending OTP to", EMAIL)
r = client.post("/auth/send_otp", json={"email": EMAIL})
print("send_otp status:", r.status_code, r.json())

otp = r.json().get("otp")
if not otp:
    print("No dev OTP returned; it may have been sent via SMTP. Cannot continue in this test.")
    sys.exit(1)

print("Attempting verify with OTP:", otp)
r2 = client.post("/auth/verify_otp", json={"email": EMAIL, "otp": otp})
print("verify_otp status:", r2.status_code, r2.json())

if r2.status_code != 200:
    print("Verify failed")
    sys.exit(1)

token = r2.json().get("access_token")
print("Got token length:", len(token))

# Call predict
payload = {"loan_amount": 1000, "term_in_months": 12, "repayment_interval": "monthly", "country": "Kenya", "activity": "Farming", "region": "Central", "partner_id": "100.0", "loan_theme_type": "General", "mpi": 0.1, "theme_loan_density": 1.0, "num_female_borrowers": 1, "num_male_borrowers": 0, "posted_year": 2020, "posted_month": 5}
headers = {"Authorization": f"Bearer {token}"}

r3 = client.post("/predict", json=payload, headers=headers)
print("predict status:", r3.status_code, r3.json())

if r3.status_code == 200:
    print("E2E OTP -> verify -> predict succeeded ✅")
else:
    print("E2E flow failed ❌")
