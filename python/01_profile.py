"""
DIG Stage D — DESCRIBE
Toronto Cleared Building Permits.

Purpose: establish what this data ACTUALLY contains before any metric is
calculated. Follows the six Describe steps from the project charter:
  1 sources  2 columns  3 GRAIN  4 keys/relationships  5 sample  6 quality

Rule in force: do NOT fix or drop anything here. Only find out what it means.
"""

import pandas as pd
import numpy as np

SRC = "data/raw/cleared_permits_since_2017.csv"
DATE_COLS = ["APPLICATION_DATE", "ISSUED_DATE", "COMPLETED_DATE"]

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 50)


def rule(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


df = pd.read_csv(SRC, dtype=str, low_memory=False)

# ---------------------------------------------------------------- step 1 + 2
rule("STEP 1-2 — SOURCE AND COLUMNS")
print(f"rows: {len(df):,}   columns: {df.shape[1]}")
print(f"memory: {df.memory_usage(deep=True).sum()/1024**2:,.0f} MB as text")

# ------------------------------------------------------------------- step 3
# GRAIN. The single most important question. What does one row represent?
rule("STEP 3 — GRAIN")
n = len(df)
uniq_permit = df["PERMIT_NUM"].nunique(dropna=False)
uniq_pair = df.groupby(["PERMIT_NUM", "REVISION_NUM"], dropna=False).ngroups

print(f"total rows                        : {n:,}")
print(f"distinct PERMIT_NUM               : {uniq_permit:,}")
print(f"distinct (PERMIT_NUM, REVISION_NUM): {uniq_pair:,}")
print(f"\nrows per permit (fan-out factor)  : {n / uniq_permit:.3f}")

if uniq_pair == n:
    print("\n=> GRAIN CONFIRMED: one row = one permit REVISION.")
    print("   (PERMIT_NUM, REVISION_NUM) is the composite primary key.")
elif uniq_permit == n:
    print("\n=> GRAIN: one row = one permit. PERMIT_NUM alone is unique.")
else:
    print(f"\n=> WARNING: neither key is unique. {n - uniq_pair:,} duplicate "
          "rows on the composite key — investigate before modelling.")

print("\nrevisions per permit, distribution:")
rev_counts = df.groupby("PERMIT_NUM").size()
print(rev_counts.value_counts().sort_index().head(12).to_string())
print(f"\nmax revisions on a single permit  : {rev_counts.max()}")
print(f"permits with >1 row               : {(rev_counts > 1).sum():,} "
      f"({(rev_counts > 1).mean():.1%})")

# THE TRAP, demonstrated with real numbers.
print("\n--- fan-out demonstration ---")
print(f"naive  COUNT(*)            = {n:,}   <- wrong 'permits' count")
print(f"correct COUNT(DISTINCT id) = {uniq_permit:,}")
print(f"overstatement              = {n - uniq_permit:,} "
      f"({(n/uniq_permit - 1):.1%})")

# ------------------------------------------------------------------- step 4
rule("STEP 4 — KEYS AND CANDIDATE DIMENSIONS (cardinality)")
for c in ["PERMIT_TYPE", "STRUCTURE_TYPE", "WORK", "STATUS", "WARD_GRID",
          "BUILDER_NAME", "CURRENT_USE", "PROPOSED_USE", "POSTAL"]:
    print(f"  {c:<32} {df[c].nunique(dropna=True):>8,} distinct   "
          f"{df[c].isna().mean():>6.1%} null")

# ------------------------------------------------------------------- step 5
rule("STEP 5 — SAMPLE (first 3 rows, key fields)")
show = ["PERMIT_NUM", "REVISION_NUM", "PERMIT_TYPE", "STATUS", "WARD_GRID",
        "APPLICATION_DATE", "ISSUED_DATE", "COMPLETED_DATE", "EST_CONST_COST"]
print(df[show].head(3).to_string(index=False))

# ------------------------------------------------------------------- step 6
rule("STEP 6 — DATA QUALITY (find, do not fix)")

print("\n-- missingness by column --")
miss = df.isna().mean().sort_values(ascending=False)
for c, v in miss.items():
    flag = "  <<<" if v > 0.20 else ""
    print(f"  {c:<34} {v:>7.2%}{flag}")

print("\n-- date parsing --")
d = pd.DataFrame(index=df.index)
for c in DATE_COLS:
    d[c] = pd.to_datetime(df[c], errors="coerce")
    bad = df[c].notna() & d[c].isna()
    print(f"  {c:<20} range {str(d[c].min())[:10]} .. {str(d[c].max())[:10]}"
          f"   unparseable: {bad.sum():,}")

print("\n-- impossible date sequences --")
checks = {
    "ISSUED before APPLICATION": (d.ISSUED_DATE < d.APPLICATION_DATE),
    "COMPLETED before ISSUED": (d.COMPLETED_DATE < d.ISSUED_DATE),
    "COMPLETED before APPLICATION": (d.COMPLETED_DATE < d.APPLICATION_DATE),
    "APPLICATION in the future": (d.APPLICATION_DATE > pd.Timestamp.today()),
    "COMPLETED in the future": (d.COMPLETED_DATE > pd.Timestamp.today()),
}
for label, mask in checks.items():
    cnt = int(mask.sum())
    print(f"  {label:<32} {cnt:>8,}  ({cnt/n:.3%})")

print("\n-- numeric fields stored as text --")
for c in ["EST_CONST_COST", "DWELLING_UNITS_CREATED", "DWELLING_UNITS_LOST"]:
    s = df[c]
    num = pd.to_numeric(s, errors="coerce")
    nonnull = s.notna().sum()
    unconvertible = int((s.notna() & num.isna()).sum())
    print(f"\n  {c}")
    print(f"    non-null            : {nonnull:,}")
    print(f"    fail numeric cast   : {unconvertible:,}")
    if unconvertible:
        ex = s[s.notna() & num.isna()].value_counts().head(5)
        print(f"    example bad values  : {list(ex.index)}")
    if num.notna().any():
        print(f"    min / median / max  : {num.min():,.0f} / "
              f"{num.median():,.0f} / {num.max():,.0f}")
        print(f"    zero or negative    : {int((num <= 0).sum()):,}")

print("\n-- cycle times (raw, unfiltered) --")
d["days_to_issue"] = (d.ISSUED_DATE - d.APPLICATION_DATE).dt.days
d["days_to_complete"] = (d.COMPLETED_DATE - d.ISSUED_DATE).dt.days
for c in ["days_to_issue", "days_to_complete"]:
    s = d[c].dropna()
    print(f"  {c:<18} n={len(s):>8,}  min={s.min():>7,.0f}  "
          f"p50={s.median():>6,.0f}  p95={s.quantile(.95):>7,.0f}  "
          f"max={s.max():>8,.0f}  negative={int((s < 0).sum()):,}")

print("\n-- STATUS values --")
print(df["STATUS"].value_counts(dropna=False).head(15).to_string())

print("\n" + "=" * 78)
print("DESCRIBE COMPLETE. Nothing has been cleaned, fixed or dropped.")
print("=" * 78)
