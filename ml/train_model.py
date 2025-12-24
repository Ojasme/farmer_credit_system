import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import LabelEncoder
import joblib
import os

print("📥 Loading processed dataset...")

df = pd.read_csv("data/processed_kiva.csv")

print("📊 Dataset shape:", df.shape)
print("📌 Columns:", df.columns.tolist())

# ===================================================
# ✅ LEAKAGE-FREE FEATURES (pre-loan only)
# ===================================================
FEATURES = [
    "loan_amount",
    "term_in_months",
    "repayment_interval",
    "country",
    "activity",
    "region",
    "partner_id",
    "loan_theme_type",
    "mpi",
    "theme_loan_density",
    "num_female_borrowers",
    "num_male_borrowers",
    "posted_year",
    "posted_month"
]

TARGET = "funded"

X = df[FEATURES]
y = df[TARGET]

# -------------------------------
# Fit encoders for categorical features
# -------------------------------
encoders = {}
categorical_features = ["repayment_interval", "country", "activity", "region", "loan_theme_type"]
for col in categorical_features:
    le = LabelEncoder()
    X[col] = le.fit_transform(X[col])
    encoders[col] = le

# partner_id is already encoded in preprocess

# -------------------------------
# Chronological Train / Test split to avoid leakage
# -------------------------------
df_sorted = df.sort_values('posted_year').reset_index(drop=True)
split_idx = int(0.8 * len(df_sorted))
X_train = df_sorted[FEATURES][:split_idx]
y_train = df_sorted[TARGET][:split_idx]
X_test = df_sorted[FEATURES][split_idx:]
y_test = df_sorted[TARGET][split_idx:]

# Encode test set
for col in categorical_features:
    X_test[col] = encoders[col].transform(X_test[col])

print("🤖 Training credit funding model (NO leakage)...")

model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    random_state=42,
    class_weight="balanced",
    n_jobs=-1
)

model.fit(X_train, y_train)

# -------------------------------
# Evaluation
# -------------------------------
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print(f"✅ Model Accuracy: {accuracy:.2f}")
print("📊 Classification Report:")
print(classification_report(y_test, y_pred))

# -------------------------------
# Save model and encoders
# -------------------------------
os.makedirs("../backend/model", exist_ok=True)
joblib.dump(model, "../backend/model/credit_model.pkl")
joblib.dump(encoders, "../backend/model/encoders.pkl")

print("💾 Model and encoders saved safely for backend")