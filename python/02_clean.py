"""
Stage: CLEAN
Applies the decisions made in logs/02-dig-describe.md. Nothing here is a
judgement call made on the fly — every rule traces to a documented finding.

Guiding principle: FLAG, DON'T DELETE.
Rows stay in the fact table with quality flags attached. Filtering happens in
SQL views, where it is visible and reversible. A row silently dropped at the
cleaning stage is a row nobody can audit later.

Outputs (to data/processed/):
    fact_permits.csv, dim_date.csv, dim_geography.csv,
    dim_permit_type.csv, dim_status.csv
"""

import pandas as pd
import numpy as np
import os

SRC = "data/raw/cleared_permits_since_2017.csv"
OUT = "data/processed"
SENTINEL = "DO NOT UPDATE OR DELETE THIS INFO FIELD"
os.makedirs(OUT, exist_ok=True)

print("reading raw...")
df = pd.read_csv(SRC, dtype=str, low_memory=False)
print(f"  {len(df):,} rows")

# ============================================================ dates
for c in ["APPLICATION_DATE", "ISSUED_DATE", "COMPLETED_DATE"]:
    df[c] = pd.to_datetime(df[c], errors="coerce")

# ============================================================ FINDING 3
# Cost. Two defects: a sentinel string, and comma thousands separators.
# Stripping commas alone recovers ~52k values a naive to_numeric discards.
cost_raw = df["EST_CONST_COST"]
is_sentinel = cost_raw.eq(SENTINEL)
cost = pd.to_numeric(
    cost_raw.where(~is_sentinel).str.replace(",", "", regex=False)
        .str.replace("$", "", regex=False).str.strip(),
    errors="coerce",
)
df["est_const_cost"] = cost.where(cost > 0)          # 0 and negatives -> null
df["cost_is_sentinel"] = is_sentinel
df["cost_is_reported"] = df["est_const_cost"].notna()

print(f"  cost: {is_sentinel.sum():,} sentinel, "
      f"{df['cost_is_reported'].sum():,} usable")

# ============================================================ FINDING 4
# WARD_GRID -> district letter + ward digits + grid digits
wg = df["WARD_GRID"].fillna("")
df["district_code"] = wg.str[0]
df["ward_code"] = wg.str[1:3]
df["grid_code"] = wg.str[3:5]

DISTRICT = {"N": "North", "S": "South", "E": "East", "W": "West"}
df["district_name"] = df["district_code"].map(DISTRICT).fillna("Unknown")

# ============================================================ FINDING 1
# Conditional permits share a permit number with the full permit.
df["is_conditional"] = df["PERMIT_TYPE"].eq("Conditional Permit")

# ============================================================ permit families
# FINDING 3 showed cost reporting splits cleanly by permit family.
TRADE = ["Plumbing(PS)", "Mechanical(MS)", "Drain and Site Service",
         "Designated Structures", "Electrical(ES)"]


def family(t):
    if pd.isna(t):
        return "Unknown"
    if t in TRADE:
        return "Trade"
    if "Demolition" in str(t):
        return "Demolition"
    return "Building"


df["permit_family"] = df["PERMIT_TYPE"].apply(family)

# ============================================================ status grouping
TERMINAL_OK = ["Closed", "Closed - Dormant"]
TERMINAL_NO = ["Cancelled", "Refused", "Abandoned", "Superseded"]


def status_group(s):
    if s in TERMINAL_OK:
        return "Completed"
    if s in TERMINAL_NO:
        return "Not Proceeded"
    return "In Progress"


df["status_group"] = df["STATUS"].apply(status_group)

# ============================================================ FINDING 2
# APPLICATION -> ISSUED is the defensible cycle time.
# ISSUED -> COMPLETED is a records-closure latency, NOT build time. Computed
# and stored for transparency, but flagged so it can never be used by accident.
df["days_to_issue"] = (df["ISSUED_DATE"] - df["APPLICATION_DATE"]).dt.days
df["days_to_admin_close"] = (df["COMPLETED_DATE"] - df["ISSUED_DATE"]).dt.days

# ============================================================ quality flags
df["flag_issued_before_applied"] = (
    df["ISSUED_DATE"].notna() & df["APPLICATION_DATE"].notna()
    & (df["ISSUED_DATE"] < df["APPLICATION_DATE"])
)
df["flag_completed_before_issued"] = (
    df["COMPLETED_DATE"].notna() & df["ISSUED_DATE"].notna()
    & (df["COMPLETED_DATE"] < df["ISSUED_DATE"])
)
df["flag_future_date"] = (
    (df["COMPLETED_DATE"] > pd.Timestamp.today())
    | (df["APPLICATION_DATE"] > pd.Timestamp.today())
)
df["flag_unknown_district"] = df["district_name"].eq("Unknown")
df["flag_never_issued"] = df["ISSUED_DATE"].isna()

# Analysis-ready = has a clean, usable review duration.
df["is_review_analysable"] = (
    df["days_to_issue"].notna()
    & (df["days_to_issue"] >= 0)
    & df["status_group"].eq("Completed")
    & ~df["flag_future_date"]
)

for c in [x for x in df.columns if x.startswith("flag_")]:
    print(f"  {c:<32} {int(df[c].sum()):>8,}")
print(f"  is_review_analysable             {int(df['is_review_analysable'].sum()):>8,}")

# ============================================================ dimensions
print("building dimensions...")

# --- dim_date
all_dates = pd.concat([df["APPLICATION_DATE"], df["ISSUED_DATE"],
                       df["COMPLETED_DATE"]]).dropna()
rng = pd.date_range(all_dates.min().normalize(),
                    all_dates.max().normalize(), freq="D")
dim_date = pd.DataFrame({"full_date": rng})
dim_date["date_key"] = dim_date.full_date.dt.strftime("%Y%m%d").astype(int)
dim_date["year"] = dim_date.full_date.dt.year
dim_date["quarter"] = dim_date.full_date.dt.quarter
dim_date["month"] = dim_date.full_date.dt.month
dim_date["month_name"] = dim_date.full_date.dt.strftime("%b")
dim_date["year_month"] = dim_date.full_date.dt.strftime("%Y-%m")
dim_date["day_of_week"] = dim_date.full_date.dt.day_name()
dim_date["is_weekend"] = dim_date.full_date.dt.dayofweek >= 5
dim_date = dim_date[["date_key", "full_date", "year", "quarter", "month",
                     "month_name", "year_month", "day_of_week", "is_weekend"]]

# --- dim_geography
# UNKNOWN MEMBER (key 0). Five source rows carry no WARD_GRID at all. Without
# this row they get a NULL foreign key, and every INNER JOIN in the views
# silently drops them -- no error, no warning, just a total that is quietly
# short. Caught by ai/qa_reviewer.py, not by eye.
# The standard dimensional fix is an explicit "Unknown" member so unmatched
# facts still join, and their unknown-ness is visible rather than invisible.
dim_geo = (df[["WARD_GRID", "district_code", "district_name", "ward_code",
               "grid_code"]]
           .drop_duplicates().dropna(subset=["WARD_GRID"])
           .sort_values("WARD_GRID").reset_index(drop=True))
dim_geo.insert(0, "geography_key", range(1, len(dim_geo) + 1))
dim_geo = dim_geo.rename(columns={"WARD_GRID": "ward_grid"})
dim_geo = pd.concat([
    pd.DataFrame([{"geography_key": 0, "ward_grid": "(none)",
                   "district_code": None, "district_name": "Unknown",
                   "ward_code": None, "grid_code": None}]),
    dim_geo], ignore_index=True)

# --- dim_permit_type
dim_type = (df[["PERMIT_TYPE", "permit_family"]].drop_duplicates()
            .dropna(subset=["PERMIT_TYPE"])
            .sort_values("PERMIT_TYPE").reset_index(drop=True))
dim_type.insert(0, "permit_type_key", range(1, len(dim_type) + 1))
dim_type = dim_type.rename(columns={"PERMIT_TYPE": "permit_type"})
# Does this type report cost? Derived from the data, not assumed.
rate = df.groupby("PERMIT_TYPE")["cost_is_reported"].mean()
dim_type["cost_reporting_rate"] = dim_type.permit_type.map(rate).round(4)
dim_type["cost_is_expected"] = dim_type.cost_reporting_rate > 0.50

# --- dim_status
dim_status = (df[["STATUS", "status_group"]].drop_duplicates()
              .dropna(subset=["STATUS"])
              .sort_values("STATUS").reset_index(drop=True))
dim_status.insert(0, "status_key", range(1, len(dim_status) + 1))
dim_status = dim_status.rename(columns={"STATUS": "status"})

print(f"  dim_date        {len(dim_date):>7,}")
print(f"  dim_geography   {len(dim_geo):>7,}")
print(f"  dim_permit_type {len(dim_type):>7,}")
print(f"  dim_status      {len(dim_status):>7,}")

# ============================================================ fact table
print("building fact table...")
f = df.copy()
f = f.merge(dim_geo[["ward_grid", "geography_key"]],
            left_on="WARD_GRID", right_on="ward_grid", how="left")
f = f.merge(dim_type[["permit_type", "permit_type_key"]],
            left_on="PERMIT_TYPE", right_on="permit_type", how="left")
f = f.merge(dim_status[["status", "status_key"]],
            left_on="STATUS", right_on="status", how="left")

for src, key in [("APPLICATION_DATE", "application_date_key"),
                 ("ISSUED_DATE", "issued_date_key"),
                 ("COMPLETED_DATE", "completed_date_key")]:
    f[key] = f[src].dt.strftime("%Y%m%d").astype("Int64")

fact = pd.DataFrame({
    "permit_num": f["PERMIT_NUM"],
    "revision_num": f["REVISION_NUM"],
    "permit_type_key": f["permit_type_key"].astype("Int64"),
    # unmatched geography -> the Unknown member, never a NULL key
    "geography_key": f["geography_key"].fillna(0).astype("Int64"),
    "status_key": f["status_key"].astype("Int64"),
    "application_date_key": f["application_date_key"],
    "issued_date_key": f["issued_date_key"],
    "completed_date_key": f["completed_date_key"],
    "structure_type": f["STRUCTURE_TYPE"],
    "work_type": f["WORK"],
    "days_to_issue": f["days_to_issue"].astype("Int64"),
    "days_to_admin_close": f["days_to_admin_close"].astype("Int64"),
    "est_const_cost": f["est_const_cost"],
    "dwelling_units_created": pd.to_numeric(f["DWELLING_UNITS_CREATED"],
                                            errors="coerce").astype("Int64"),
    "dwelling_units_lost": pd.to_numeric(f["DWELLING_UNITS_LOST"],
                                         errors="coerce").astype("Int64"),
    "cost_is_sentinel": f["cost_is_sentinel"],
    "cost_is_reported": f["cost_is_reported"],
    "is_conditional": f["is_conditional"],
    "flag_issued_before_applied": f["flag_issued_before_applied"],
    "flag_completed_before_issued": f["flag_completed_before_issued"],
    "flag_future_date": f["flag_future_date"],
    "flag_unknown_district": f["flag_unknown_district"],
    "flag_never_issued": f["flag_never_issued"],
    "is_review_analysable": f["is_review_analysable"],
})
fact.insert(0, "permit_sk", range(1, len(fact) + 1))

assert len(fact) == len(df), "row count changed during fact build"
print(f"  fact_permits    {len(fact):>7,}  (row count preserved)")

# ============================================================ write
dim_date.to_csv(f"{OUT}/dim_date.csv", index=False)
dim_geo.to_csv(f"{OUT}/dim_geography.csv", index=False)
dim_type.to_csv(f"{OUT}/dim_permit_type.csv", index=False)
dim_status.to_csv(f"{OUT}/dim_status.csv", index=False)
fact.to_csv(f"{OUT}/fact_permits.csv", index=False)
print(f"\nwritten to {OUT}/")
