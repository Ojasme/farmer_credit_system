import pandas as pd
from sklearn.preprocessing import LabelEncoder
import os

print("📥 Loading datasets...")

# Load raw datasets
loans = pd.read_csv("data/kiva_loans.csv")
mpi = pd.read_csv("data/kiva_mpi_region_locations.csv")
themes_region = pd.read_csv("data/loan_themes_by_region.csv")
themes_ids = pd.read_csv("data/loan_theme_ids.csv")

# Merge loan themes
loans = loans.merge(themes_ids[['id', 'Loan Theme ID', 'Loan Theme Type']], on='id', how='left')
loans.rename(columns={'Loan Theme ID': 'loan_theme_id', 'Loan Theme Type': 'loan_theme_type'}, inplace=True)

# Filter to agriculture sector for farmer credit
loans = loans[loans['sector'] == 'Agriculture']

# -------------------------------
# Base loan features (pre-loan only)
# -------------------------------
df = loans[
    [
        "loan_amount",
        "term_in_months",
        "repayment_interval",
        "borrower_genders",
        "country",
        "activity",
        "region",
        "partner_id",
        "loan_theme_id",
        "loan_theme_type",
        "posted_time"  # for time-based split
    ]
].dropna()

# -------------------------------
# Target: funded (1 = fully funded, 0 = not)
# -------------------------------
df["funded"] = (loans.loc[df.index, 'funded_amount'] == loans.loc[df.index, 'loan_amount']).astype(int)

# -------------------------------
# Add MPI (poverty index by country)
# -------------------------------
mpi_country = mpi.groupby("country")["MPI"].mean().reset_index()
mpi_country.rename(columns={'MPI': 'mpi'}, inplace=True)
df = df.merge(mpi_country, on="country", how="left")
df["mpi"].fillna(df["mpi"].median(), inplace=True)

# -------------------------------
# Loan theme enrichment
# -------------------------------
theme_density = themes_region.groupby(["country", "Loan Theme ID"]).size().reset_index(name="theme_loan_density")
theme_density.rename(columns={'Loan Theme ID': 'loan_theme_id'}, inplace=True)
df = df.merge(theme_density, on=["country","loan_theme_id"], how="left")
df["theme_loan_density"].fillna(df["theme_loan_density"].median(), inplace=True)

# Drop raw theme ID
df.drop("loan_theme_id", axis=1, inplace=True)

# -------------------------------
# Feature engineering
# -------------------------------
# Borrower genders: count females
df['borrower_genders'] = df['borrower_genders'].fillna('')
df['num_female_borrowers'] = df['borrower_genders'].apply(lambda x: x.count('female'))
df['num_male_borrowers'] = df['borrower_genders'].apply(lambda x: x.count('male'))
df.drop("borrower_genders", axis=1, inplace=True)

# Activity: encode
# For simplicity, label encode
le_activity = LabelEncoder()
df['activity'] = le_activity.fit_transform(df['activity'])

# -------------------------------
# Encode categorical variables
# -------------------------------
label_mappings = {}
categorical_cols = ["repayment_interval", "country", "region", "loan_theme_type"]
for col in categorical_cols:
    le = LabelEncoder()
    df[col] = le.fit_transform(df[col])
    label_mappings[col] = {str(label): idx for idx, label in enumerate(le.classes_)}

# Activity: encode
# For simplicity, label encode
le_activity = LabelEncoder()
df['activity'] = le_activity.fit_transform(df['activity'])
label_mappings['activity'] = {str(label): idx for idx, label in enumerate(le_activity.classes_)}

# -------------------------------
# Handle dates: convert posted_time to datetime, extract features
# -------------------------------
df['posted_time'] = pd.to_datetime(df['posted_time'])
df['posted_year'] = df['posted_time'].dt.year
df['posted_month'] = df['posted_time'].dt.month
df.drop("posted_time", axis=1, inplace=True)

# -------------------------------
# Drop any remaining leaky or unnecessary
# -------------------------------
# partner_id: perhaps keep or encode
le_partner = LabelEncoder()
df['partner_id'] = le_partner.fit_transform(df['partner_id'].astype(str))
label_mappings['partner_id'] = {str(label): idx for idx, label in enumerate(le_partner.classes_)}

# -------------------------------
# Save processed dataset
# -------------------------------
os.makedirs("data", exist_ok=True)
df.to_csv("data/processed_kiva.csv", index=False)

# Save label mappings for frontend
import json
print("Label mappings:", label_mappings)
with open("data/label_mappings.json", "w") as f:
    json.dump(label_mappings, f)

print("✅ Preprocessing complete")
print("📊 Columns:", df.columns.tolist())
print("📊 Shape:", df.shape)
print("📊 Funded distribution:", df['funded'].value_counts())