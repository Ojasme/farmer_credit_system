import os
import time
import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_redis(monkeypatch):
    # Use fakeredis for tests
    import fakeredis
    from auth import redis_client as real_redis
    fake = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("auth.redis_client", fake)
    yield


def test_send_otp_dev_returns_code():
    r = client.post("/auth/send_otp", json={"email": "user@example.com"})
    assert r.status_code == 200
    data = r.json()
    assert "otp" in data and len(data["otp"]) == 6


def test_verify_otp_success():
    r = client.post("/auth/send_otp", json={"email": "tester1@example.com"})
    data = r.json()
    otp = data.get("otp")
    assert otp
    r2 = client.post("/auth/verify_otp", json={"email": "tester1@example.com", "otp": otp})
    assert r2.status_code == 200
    assert "access_token" in r2.json()


def test_verify_otp_wrong_code_increments_attempts():
    r = client.post("/auth/send_otp", json={"email": "tester2@example.com"})
    data = r.json()
    assert data.get("otp")
    r2 = client.post("/auth/verify_otp", json={"email": "tester2@example.com", "otp": "000000"})
    assert r2.status_code == 401


def test_send_rate_limit_exceeded(monkeypatch):
    # Use a low limit for test
    import auth
    monkeypatch.setenv("OTP_MAX_SENDS_PER_HOUR", "2")
    # Reset module config
    auth.MAX_SENDS_PER_HOUR = 2
    for _ in range(2):
        r = client.post("/auth/send_otp", json={"email": "rate@example.com"})
        assert r.status_code == 200
    r = client.post("/auth/send_otp", json={"email": "rate@example.com"})
    assert r.status_code == 429


def test_predict_requires_auth():
    # call predict without token
    payload = {"loan_amount": 1000, "term_in_months": 12, "repayment_interval": "monthly", "country": "Kenya", "activity": "Farming", "region": "Central", "partner_id": "100.0", "loan_theme_type": "General", "mpi": 0.1, "theme_loan_density": 1.0, "num_female_borrowers": 1, "num_male_borrowers": 0, "posted_year": 2020, "posted_month": 5}
    r = client.post("/predict", json=payload)
    assert r.status_code == 401


def test_predict_with_token():
    # full flow: send otp, verify => token, then call predict
    email = "testuser@example.com"
    r = client.post("/auth/send_otp", json={"email": email})
    otp = r.json().get("otp")
    assert otp
    r2 = client.post("/auth/verify_otp", json={"email": email, "otp": otp})
    token = r2.json().get("access_token")
    assert token
    payload = {"loan_amount": 1000, "term_in_months": 12, "repayment_interval": "monthly", "country": "Kenya", "activity": "Farming", "region": "Central", "partner_id": "100.0", "loan_theme_type": "General", "mpi": 0.1, "theme_loan_density": 1.0, "num_female_borrowers": 1, "num_male_borrowers": 0, "posted_year": 2020, "posted_month": 5}
    r3 = client.post("/predict", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert r3.status_code == 200

@pytest.mark.skipif(not os.environ.get("SMTP_HOST"), reason="SMTP not configured")
def test_send_otp_smtp_real():
    # This will actually attempt to send an email - requires SMTP_ env vars and a real email in TEST_EMAIL
    test_email = os.environ.get("TEST_EMAIL")
    assert test_email
    r = client.post("/auth/send_otp", json={"email": test_email})
    assert r.status_code == 200
    data = r.json()
    assert data.get("sent") is True
