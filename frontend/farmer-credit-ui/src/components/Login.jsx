import { useState } from "react";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export default function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [step, setStep] = useState(0); // 0 = enter email, 1 = enter otp
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const validEmail = (e) => /\S+@\S+\.\S+/.test(e);

  const sendOtp = async () => {
    setError(null);
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/auth/send_otp`, { email });
      if (res.data.sent === false && res.data.otp) {
        // Dev mode - OTP returned in response
        alert(`Dev OTP: ${res.data.otp}`);
      }
      setStep(1);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Network Error";
      setError(msg);
    }
    setLoading(false);
  };

  const verifyOtp = async () => {
    setError(null);
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/auth/verify_otp`, { email, otp });
      const token = res.data.access_token;
      localStorage.setItem("access_token", token);
      onLogin(token);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Network Error";
      setError(msg);
    }
    setLoading(false);
  };

  return (
    <div className="login-container">
      <h2>Login with email OTP</h2>
      {error && <div style={{color: 'red', marginBottom: 8}}>{error}</div>}

      {step === 0 && (
        <div>
          <label>Email address</label>
          <input name="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
          <button onClick={sendOtp} disabled={loading || !validEmail(email)}>Send OTP</button>
        </div>
      )}

      {step === 1 && (
        <div>
          <label>Enter OTP</label>
          <input name="otp" value={otp} onChange={(e) => setOtp(e.target.value)} />
          <button onClick={verifyOtp} disabled={loading || !otp}>{loading ? 'Verifying...' : 'Verify OTP'}</button>
        </div>
      )}
    </div>
  );
}
