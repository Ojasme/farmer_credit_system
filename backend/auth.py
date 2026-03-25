"""
Auth helpers: Redis-backed OTP, Twilio send, JWT helpers, and FastAPI dependencies
"""
import os
import random
import datetime
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import HTTPException, status, Depends, Request
import jwt
from twilio.rest import Client as TwilioClient

from redis_client import redis_client
import logging

# If Redis is unreachable at import time (dev env), fall back to fakeredis in-memory store
REDIS_AVAILABLE = True
try:
    # attempt a ping to verify connectivity
    redis_client.ping()
except Exception as e:
    REDIS_AVAILABLE = False
    logging.warning(f"Redis not reachable ({e}), falling back to in-memory fakeredis for development")
    try:
        import fakeredis
        redis_client = fakeredis.FakeRedis(decode_responses=True)
    except Exception:
        logging.exception("Failed to import fakeredis for fallback; Redis operations will fail")

# Config
OTP_TTL_SECONDS = int(os.environ.get("OTP_TTL_SECONDS", 300))  # 5 minutes
MAX_VERIFY_ATTEMPTS = int(os.environ.get("OTP_MAX_ATTEMPTS", 5))
MAX_SENDS_PER_HOUR = int(os.environ.get("OTP_MAX_SENDS_PER_HOUR", 5))
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret")
JWT_ALGORITHM = "HS256"
JWT_EXP_SECONDS = int(os.environ.get("JWT_EXP_SECONDS", 60 * 60 * 24))  # 1 day

# SMTP / Email config (used instead of Twilio for email OTPs)
SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")
EMAIL_FROM = os.environ.get("EMAIL_FROM")


def _generate_otp() -> str:
    return f"{random.randint(0, 999999):06d}"


def _send_email_via_smtp(to_email: str, subject: str, body: str) -> tuple[bool, str]:
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS and EMAIL_FROM):
        return False, "SMTP not configured"
    try:
        import smtplib
        from email.message import EmailMessage
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = EMAIL_FROM
        msg["To"] = to_email
        msg.set_content(body)
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True, "sent"
    except Exception as e:
        logging.exception("SMTP send failed")
        return False, str(e)


# Redis keys (email-based)
def _otp_key(email: str) -> str:
    return f"otp:{email}"


def _send_count_key(email: str) -> str:
    return f"otp_send_count:{email}"


# OTP operations
def set_otp(email: str, code: str, ttl: int = OTP_TTL_SECONDS):
    key = _otp_key(email)
    try:
        # store as a hash with code and attempts
        redis_client.hset(key, mapping={"code": code, "attempts": 0})
        redis_client.expire(key, ttl)
    except Exception as e:
        logging.exception("Redis set_otp failed")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OTP service unavailable (cache error)")


def get_otp_record(email: str) -> Optional[dict]:
    key = _otp_key(email)
    try:
        if not redis_client.exists(key):
            return None
        rec = redis_client.hgetall(key)
    except Exception as e:
        logging.exception("Redis get_otp_record failed")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OTP service unavailable (cache error)")

    # attempts comes as string, convert
    if "attempts" in rec:
        try:
            rec["attempts"] = int(rec["attempts"])
        except Exception:
            rec["attempts"] = 0
    return rec


def delete_otp(email: str):
    try:
        redis_client.delete(_otp_key(email))
    except Exception:
        logging.exception("Redis delete_otp failed")
        # best-effort delete; ignore in production fallback
        pass


def incr_attempts(email: str) -> int:
    key = _otp_key(email)
    try:
        return redis_client.hincrby(key, "attempts", 1)
    except Exception:
        logging.exception("Redis incr_attempts failed")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OTP service unavailable (cache error)")


def increment_send_count(email: str) -> int:
    key = _send_count_key(email)
    try:
        val = redis_client.incr(key)
        # set TTL to 1 hour on first increment
        if redis_client.ttl(key) == -1:
            redis_client.expire(key, 3600)
        return int(val)
    except Exception:
        logging.exception("Redis increment_send_count failed")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OTP service unavailable (cache error)")


def send_otp_service(email: str) -> dict:
    # basic email validation
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Valid email required")

    # rate limit sends
    sends = increment_send_count(email)
    if sends > MAX_SENDS_PER_HOUR:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many OTP requests. Try later.")

    code = _generate_otp()
    set_otp(email, code)

    # send via SMTP if configured
    sent, info = _send_email_via_smtp(email, "Your verification code", f"Your verification code: {code}")
    if sent:
        return {"sent": True, "message": "OTP sent"}

    # dev fallback: return the code
    return {"sent": False, "message": "SMTP not configured - returning OTP in response for dev", "otp": code}


def verify_otp_service(email: str, otp: str) -> str:
    rec = get_otp_record(email)
    if not rec:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No OTP requested for this email")

    # check expiry: if key exists, TTL available. If TTL expired, get_otp_record would return None
    if rec.get("attempts", 0) >= MAX_VERIFY_ATTEMPTS:
        delete_otp(email)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Max verification attempts exceeded")

    if otp != rec.get("code"):
        incr_attempts(email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP")

    # success
    delete_otp(email)
    payload = {
        "sub": email,
        "iat": int(datetime.datetime.utcnow().timestamp()),
        "exp": int((datetime.datetime.utcnow() + datetime.timedelta(seconds=JWT_EXP_SECONDS)).timestamp()),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

# JWT / dependency
def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_current_user(request: Request):
    auth: str = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header missing")
    token = auth.split(" ", 1)[1]
    payload = decode_token(token)
    return payload.get("sub")
