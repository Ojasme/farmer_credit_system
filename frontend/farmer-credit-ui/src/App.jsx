import { useState, useEffect } from "react";
import axios from "axios";
import "./App.css";

function App() {
  const [form, setForm] = useState({
    loan_amount: "",
    term_in_months: "",
    repayment_interval: "",
    country: "",
    activity: "",
    region: "",
    partner_id: "",
    loan_theme_type: "",
    mpi: "",
    theme_loan_density: "",
    num_female_borrowers: "",
    num_male_borrowers: "",
    posted_year: "",
    posted_month: ""
  });

  const [mappings, setMappings] = useState({});
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Sample mappings based on data
    setMappings({
      repayment_interval: ["monthly", "irregular", "bullet"],
      country: ["Philippines", "Kenya", "Cambodia", "Pakistan", "Peru", "Colombia", "Ecuador", "Nicaragua", "Tanzania", "Ghana"],
      activity: ["Farming", "Livestock", "Poultry", "Agriculture", "Dairy", "Crops", "Fisheries", "Forestry", "Beekeeping", "Animal Husbandry"],
      region: ["Central", "North", "South", "East", "West", "Northeast", "Southeast", "Northwest", "Southwest", "Central Region"],
      loan_theme_type: ["General", "Agriculture", "Women Entrepreneurs", "Underserved", "Rural Inclusion", "Green", "Youth", "Vulnerable Populations", "Startup", "Micro-enterprise"],
      partner_id: ["100.0", "151.0", "123.0", "138.0", "145.0", "156.0", "169.0", "183.0", "190.0", "199.0"]
    });
  }, []);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const submitForm = async () => {
    setLoading(true);
    try {
      const response = await axios.post("http://localhost:8000/predict", form);
      setResult(response.data);
    } catch (err) {
      alert("Backend not running or error: " + err.message);
    }
    setLoading(false);
  };

  return (
    <div className="container">
      <h1>🌾 Farmer Credit Assessment System</h1>
      <p className="subtitle">Predict loan funding probability for agriculture loans</p>

      <div className="form-grid">
        <div className="form-group">
          <label>Loan Amount ($)</label>
          <input type="number" name="loan_amount" value={form.loan_amount} onChange={handleChange} />
        </div>

        <div className="form-group">
          <label>Term in Months</label>
          <input type="number" name="term_in_months" value={form.term_in_months} onChange={handleChange} />
        </div>

        <div className="form-group">
          <label>Repayment Interval</label>
          <select name="repayment_interval" value={form.repayment_interval} onChange={handleChange}>
            <option value="">Select</option>
            {mappings.repayment_interval?.map(opt => <option key={opt} value={opt}>{opt}</option>)}
          </select>
        </div>

        <div className="form-group">
          <label>Country</label>
          <select name="country" value={form.country} onChange={handleChange}>
            <option value="">Select</option>
            {mappings.country?.map(opt => <option key={opt} value={opt}>{opt}</option>)}
          </select>
        </div>

        <div className="form-group">
          <label>Activity</label>
          <select name="activity" value={form.activity} onChange={handleChange}>
            <option value="">Select</option>
            {mappings.activity?.map(opt => <option key={opt} value={opt}>{opt}</option>)}
          </select>
        </div>

        <div className="form-group">
          <label>Region</label>
          <select name="region" value={form.region} onChange={handleChange}>
            <option value="">Select</option>
            {mappings.region?.map(opt => <option key={opt} value={opt}>{opt}</option>)}
          </select>
        </div>

        <div className="form-group">
          <label>Partner ID</label>
          <select name="partner_id" value={form.partner_id} onChange={handleChange}>
            <option value="">Select</option>
            {mappings.partner_id?.map(opt => <option key={opt} value={opt}>{opt}</option>)}
          </select>
        </div>

        <div className="form-group">
          <label>Loan Theme Type</label>
          <select name="loan_theme_type" value={form.loan_theme_type} onChange={handleChange}>
            <option value="">Select</option>
            {mappings.loan_theme_type?.map(opt => <option key={opt} value={opt}>{opt}</option>)}
          </select>
        </div>

        <div className="form-group">
          <label>MPI (Poverty Index)</label>
          <input type="number" step="0.01" name="mpi" value={form.mpi} onChange={handleChange} />
        </div>

        <div className="form-group">
          <label>Theme Loan Density</label>
          <input type="number" name="theme_loan_density" value={form.theme_loan_density} onChange={handleChange} />
        </div>

        <div className="form-group">
          <label>Num Female Borrowers</label>
          <input type="number" name="num_female_borrowers" value={form.num_female_borrowers} onChange={handleChange} />
        </div>

        <div className="form-group">
          <label>Num Male Borrowers</label>
          <input type="number" name="num_male_borrowers" value={form.num_male_borrowers} onChange={handleChange} />
        </div>
<div>
   
</div>
        <div className="form-group">
          <label>Posted Year</label>
          <input type="number" name="posted_year" value={form.posted_year} onChange={handleChange} />
        </div>

        <div className="form-group">
          <label>Posted Month</label>
          <input type="number" min="1" max="12" name="posted_month" value={form.posted_month} onChange={handleChange} />
        </div>
      </div>

      <button onClick={submitForm} disabled={loading}>
        {loading ? "Predicting..." : "Predict Funding"}
      </button>

      {result && (
        <div className="result">
          <h2>Prediction Result</h2>
          <p>Probability: {(result.funded_probability * 100).toFixed(2)}%</p>
          <p>Prediction: {result.prediction}</p>
          <p>Recommendation: {result.recommendation}</p>
        </div>
      )}
    </div>
  ); 
}

export default App;