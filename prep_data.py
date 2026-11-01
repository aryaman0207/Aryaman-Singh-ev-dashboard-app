"""Run once: makes a small CSV (only the columns the app needs)."""
import pandas as pd

SOURCE = "Electric_Vehicle_Population_Data.csv"

# canonical name -> (exact match after cleaning, keyword fallback)
RULES = {
    "DOL Vehicle ID": ("dol vehicle id", "vehicle id"),
    "State": ("state", None),
    "Model Year": ("model year", None),
    "Make": ("make", None),
    "Model": ("model", None),
    "Electric Vehicle Type": ("electric vehicle type", "vehicle type"),
    "Clean Alternative Fuel Vehicle (CAFV) Eligibility": (
        "clean alternative fuel vehicle (cafv) eligibility",
        "cafv",
    ),
    "Electric Range": ("electric range", None),
}


def clean(name):
    return " ".join(str(name).replace("\ufeff", "").split()).lower()


header = pd.read_csv(SOURCE, nrows=0).columns.tolist()
print("Columns found in your CSV:")
for c in header:
    print("   ", repr(c))

mapping = {}
missing = []
for canonical, (exact, keyword) in RULES.items():
    found = next((c for c in header if clean(c) == exact), None)
    if found is None and keyword:
        found = next((c for c in header if keyword in clean(c)), None)
    if found is None:
        missing.append(canonical)
    else:
        mapping[found] = canonical

# Fallback for the vehicle type column: find it by its VALUES (contains BEV / PHEV)
if "Electric Vehicle Type" in missing:
    sample = pd.read_csv(SOURCE, nrows=3000)
    for col in sample.columns:
        if col in mapping:
            continue
        vals = sample[col].astype(str).str.upper()
        if vals.str.contains("BEV").any() and vals.str.contains("PHEV").any():
            mapping[col] = "Electric Vehicle Type"
            missing.remove("Electric Vehicle Type")
            print("\nUsing column", repr(col), "as 'Electric Vehicle Type' (matched by its values)")
            break

if missing:
    print("\nCould NOT find these columns:", missing)
    print("Copy the list of columns above and send it to Claude.")
    raise SystemExit(1)

df = pd.read_csv(SOURCE, usecols=list(mapping.keys())).rename(columns=mapping)
df.to_csv("ev_data_small.csv", index=False)
print("\nDone! Created ev_data_small.csv with rows:", len(df))
