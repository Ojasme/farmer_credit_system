#!/usr/bin/env python3
"""Simple script to send a live OTP using configured SMTP/email credentials (or return dev OTP).

Usage:
  python scripts/send_live_otp.py [email]

If no email is provided, the script will use TEST_EMAIL from env.
"""
import sys
import os
from pathlib import Path
# Ensure backend root is on sys.path so we can import package modules
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from dotenv import load_dotenv
load_dotenv()

from auth import send_otp_service


def main():
    email = None
    if len(sys.argv) > 1:
        email = sys.argv[1]
    else:
        email = os.environ.get("TEST_EMAIL")

    if not email:
        print("No email provided and TEST_EMAIL not set. Provide an email as an argument or set TEST_EMAIL in .env")
        return

    print(f"Sending OTP to {email} ...")
    try:
        res = send_otp_service(email)
        print("Result:", res)
    except Exception as e:
        print("Error:", e)


if __name__ == '__main__':
    main()
