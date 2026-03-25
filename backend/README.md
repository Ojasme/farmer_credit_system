## Backend — Farmer Credit API

Setup

- Create a Python virtual environment and activate it:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

- Install dependencies:

```bash
pip install -r requirements.txt
```

Run (development)

```bash
# from backend/
npm run dev    # runs: python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Run (production)

```bash
npm start      # runs: python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Notes

- CORS is enabled in `main.py` allowing the frontend to call the API during development.
- Frontend dev server runs on port 5173 by default; the backend listens on port 8000. Configure Axios or fetch in the frontend to use `http://localhost:8000` as the API base URL.

Environment variables (recommended)

- `JWT_SECRET` — secret for signing JWTs (default `dev-secret`)
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `EMAIL_FROM` — set these to send real OTP emails via an SMTP provider
- `TEST_EMAIL` — email address used in integration tests when SMTP is enabled
- `REDIS_URL` or `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB` — Redis connection (defaults to localhost:6379)
- `OTP_TTL_SECONDS`, `OTP_MAX_ATTEMPTS`, `OTP_MAX_SENDS_PER_HOUR` — OTP configuration

Testing

- Unit & integration tests are in `backend/tests`. They use `fakeredis` so you can run them without a Redis server.
- The Twilio integration test is skipped unless `TWILIO_ACCOUNT_SID` is set and `TEST_PHONE` is provided.

SMTP setup & live test

1. Obtain SMTP credentials from your email provider (Gmail, SendGrid, Mailgun, etc.).
2. The values required are:
   - SMTP_HOST
   - SMTP_PORT (usually 587)
   - SMTP_USER
   - SMTP_PASS
   - EMAIL_FROM (the From address used when sending OTPs)
3. Create a `.env` in `backend/` (copy `.env.example`) and set these values, plus a `TEST_EMAIL` for live testing:

   SMTP_HOST=smtp.example.com
   SMTP_PORT=587
   SMTP_USER=you@example.com
   SMTP_PASS=supersecret
   EMAIL_FROM=notify@example.com
   TEST_EMAIL=test@example.com

4. Run the quick live test (from project root):

   /usr/bin/python3 backend/scripts/send_live_otp.py  # uses TEST_EMAIL from .env
   # or
   /usr/bin/python3 backend/scripts/send_live_otp.py recipient@example.com  # specify email directly

5. Expected results:
   - If SMTP is configured properly you'll see `{"sent": True, "message": "OTP sent"}` and an email delivered to the destination address
   - If SMTP is not configured the script prints the dev OTP for quick local testing

If you prefer, set the SMTP env vars and `TEST_EMAIL` and tell me when to run the live test here and I can run the script; otherwise run it locally and paste any errors and I'll help debug.
