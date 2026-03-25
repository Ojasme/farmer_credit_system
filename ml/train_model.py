import pandas as pd
import joblib
import os
import json
import numpy as np

from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score, roc_auc_score
from imblearn.over_sampling import SMOTE

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

# Use label mappings saved by preprocess (if present)
label_map_path = os.path.join("data", "label_mappings.json")
label_mappings = {}
if os.path.exists(label_map_path):
    with open(label_map_path, "r") as f:
        label_mappings = json.load(f)

X = df[FEATURES].copy()
y = df[TARGET]

# If any categorical columns are still object/string, map using label_mappings
for col, mapping in label_mappings.items():
    if col in X.columns and X[col].dtype == object:
        # mapping keys in file are strings; convert as needed
        X[col] = X[col].astype(str).map(mapping).fillna(0).astype(int)

# -------------------------------
# Chronological Train / Test split to avoid leakage
# -------------------------------
# sort by year and month for time-safety
df_sorted = df.sort_values(["posted_year", "posted_month"]).reset_index(drop=True)
split_idx = int(0.8 * len(df_sorted))
X_train = df_sorted[FEATURES][:split_idx].copy()
y_train = df_sorted[TARGET][:split_idx].copy()
X_test = df_sorted[FEATURES][split_idx:].copy()
y_test = df_sorted[TARGET][split_idx:].copy()

# If label_mappings present, apply to train/test to be safe
for col, mapping in label_mappings.items():
    if col in X_train.columns and X_train[col].dtype == object:
        X_train[col] = X_train[col].astype(str).map(mapping).fillna(0).astype(int)
    if col in X_test.columns and X_test[col].dtype == object:
        X_test[col] = X_test[col].astype(str).map(mapping).fillna(0).astype(int)

# -------------------------------
# Handle class imbalance with SMOTE on training set
# -------------------------------
print("🔁 Applying SMOTE to training data...")
smote = SMOTE(random_state=42)
X_train_res, y_train_res = smote.fit_resample(X_train.drop(["posted_year", "posted_month"], axis=1), y_train)

# Keep test set without SMOTE, drop date cols for model
X_test_model = X_test.drop(["posted_year", "posted_month"], axis=1)

# -------------------------------
# XGBoost Model (CONTROLLED CONFIDENCE)
# -------------------------------
model = XGBClassifier(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=5,
    min_child_weight=3,
    subsample=0.75,
    colsample_bytree=0.75,
    gamma=0.5,
    objective="binary:logistic",
    eval_metric="auc",
    random_state=42,
    n_jobs=-1
)

print("🚀 Training XGBoost...")
model.fit(X_train_res, y_train_res)

# -------------------------------
# Evaluation + threshold optimization for rejected loans (class 0)
# -------------------------------
y_prob = model.predict_proba(X_test_model)[:, 1]
y_pred_default = model.predict(X_test_model)

print(f"Accuracy (default 0.5): {accuracy_score(y_test, y_pred_default):.4f}")
print(f"AUC: {roc_auc_score(y_test, y_prob):.4f}")
print(classification_report(y_test, y_pred_default))

# optimize threshold to better detect rejected loans (class 0)
best_threshold = 0.5
best_f1 = -1
for t in np.arange(0.3, 0.8, 0.01):
    y_pred_t = (y_prob >= t).astype(int)
    f1 = f1_score(y_test, y_pred_t, pos_label=0)
    if f1 > best_f1:
        best_f1 = f1
        best_threshold = float(t)

print(f"Best threshold for rejected loans (class 0): {best_threshold:.2f} (f1={best_f1:.3f})")

# -------------------------------
# Save model, mappings and threshold
# -------------------------------
os.makedirs("../backend/model", exist_ok=True)
joblib.dump(model, "../backend/model/credit_model.pkl")
with open("../backend/model/label_mappings.json", "w") as f:
    json.dump(label_mappings, f)
with open("../backend/model/threshold.json", "w") as f:
    json.dump({"best_threshold": best_threshold}, f)

print("💾 Model, mappings, and threshold saved to ../backend/model")