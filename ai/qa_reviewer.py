#!/usr/bin/env python3
"""
qa_reviewer.py — the safety net. Re-checks the analysis against itself.

WHAT THIS IS FOR
----------------
Every finding in this project rests on assumptions that were true of the
September 2026 extract. Toronto refreshes this dataset daily. Assumptions rot.

This runs every one of them as an assertion and says, out loud, which still
hold. It is the difference between "the analysis was right" and "the analysis
is right."

ACHIEVE ASSESSMENT (per the project charter)
--------------------------------------------
A - Aiding coordination   NO.
C - Cutting tedium        YES. Re-checking 14 invariants by hand takes an hour
                          and is exactly the job a person quietly stops doing.
H - Safety net            YES. This is the whole purpose.
I - Better problem-solving PARTIAL. It says what broke, not why.
E - Scaling               YES. Runs on every refresh, unattended, forever.

Three and a half of five. Earns its place.

NOTE ON WHAT IS AND IS NOT AI HERE
----------------------------------
Almost nothing in this file is a language model, and that is deliberate.
A data-quality check must be deterministic and reproducible; asking a model
"does this look right?" produces a different answer on a different day.

AI's contribution was writing the checks — turning a human's list of "things
that must stay true" into executable assertions (ACHIEVE-C). The optional
--explain flag sends only FAILED check names to a model for a plain-language
summary. The verdicts themselves are arithmetic.

An AI that grades its own homework is not a safety net.

USAGE
    python ai/qa_reviewer.py
    python ai/qa_reviewer.py --explain      # plain-language summary of failures
Exit code 0 = all pass, 1 = at least one failure.
"""

import os
import sys

try:
    import psycopg2
except ImportError:
    sys.exit("psycopg2 not installed. pip install psycopg2-binary")

DB = dict(dbname="toronto_permits", user="root", host="/var/run/postgresql")

# Baselines recorded from the 2026-09-20 extract. A check that drifts from
# these is not necessarily a bug - it may be real change in the data - but it
# must be seen and explained, never discovered later by a stakeholder.
BASE = {
    "source_rows": 438949,
    "distinct_permits": 393521,
    "sentinel_rows": 222734,
    "fair_records": 145326,
    "fair_permits": 136241,
    "median_2017": 20.0,
    "median_2022": 29.0,
    "median_2025": 18.0,
}

results = []


def check(name, ok, detail, why):
    results.append((name, bool(ok), detail, why))


def q1(cur, sql):
    cur.execute(sql)
    r = cur.fetchone()
    return r[0] if r else None


FAIR_WHERE = """
  f.is_review_analysable
  AND f.days_to_admin_close BETWEEN 0 AND 365
  AND da.year BETWEEN 2017 AND 2025
"""


def median_for_year(cur, yr):
    return q1(cur, f"""
SELECT ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.days_to_issue)::numeric,1)
FROM permits.fact_permits f
JOIN permits.dim_date da ON da.date_key = f.application_date_key
WHERE {FAIR_WHERE} AND da.year = {yr}""")


def main():
    con = psycopg2.connect(**DB)
    cur = con.cursor()

    # -------------------------------------------------- structural integrity
    n = q1(cur, "SELECT COUNT(*) FROM permits.fact_permits")
    check("row count matches source", n == BASE["source_rows"],
          f"{n:,} (baseline {BASE['source_rows']:,})",
          "A changed row count means the extract changed. Every figure below "
          "is then describing a different dataset than the write-up does.")

    d = q1(cur, "SELECT COUNT(DISTINCT permit_num) FROM permits.fact_permits")
    check("distinct permits matches", d == BASE["distinct_permits"],
          f"{d:,} (baseline {BASE['distinct_permits']:,})", "")

    # THE grain check. If this ever passes trivially it means someone
    # deduplicated the fact table and silently destroyed conditional permits.
    check("fan-out still present (rows > permits)", n > d,
          f"{n - d:,} extra rows = {(n/d - 1):.1%} overstatement",
          "If rows == permits, someone has deduplicated the fact table. That "
          "deletes the conditional-permit pairs described in Finding 1.")

    orphans = q1(cur, """
SELECT COUNT(*) FROM permits.fact_permits f
LEFT JOIN permits.dim_permit_type t ON t.permit_type_key = f.permit_type_key
LEFT JOIN permits.dim_geography g   ON g.geography_key   = f.geography_key
LEFT JOIN permits.dim_status s      ON s.status_key      = f.status_key
WHERE t.permit_type_key IS NULL OR g.geography_key IS NULL OR s.status_key IS NULL""")
    check("no orphaned dimension keys", orphans == 0, f"{orphans:,} orphans",
          "An orphan silently drops rows from every inner-join query, so totals "
          "shrink without any error appearing.")

    dup = q1(cur, """
SELECT COUNT(*) FROM (
  SELECT permit_sk FROM permits.fact_permits GROUP BY 1 HAVING COUNT(*) > 1
) x""")
    check("surrogate key unique", dup == 0, f"{dup:,} duplicated permit_sk", "")

    # ------------------------------------------------------ data quality
    sent = q1(cur, "SELECT COUNT(*) FROM permits.fact_permits WHERE cost_is_sentinel")
    check("cost sentinel count stable", sent == BASE["sentinel_rows"],
          f"{sent:,} (baseline {BASE['sentinel_rows']:,})",
          "The placeholder string is a City data-entry artifact. A change means "
          "their process changed - worth knowing before publishing cost figures.")

    both = q1(cur, """
SELECT COUNT(*) FROM permits.fact_permits
WHERE cost_is_sentinel AND cost_is_reported""")
    check("sentinel and reported are mutually exclusive", both == 0,
          f"{both:,} rows flagged as both",
          "These flags contradict each other by definition. Any row with both "
          "means the cleaning logic has a bug.")

    neg = q1(cur, """
SELECT COUNT(*) FROM permits.fact_permits
WHERE is_review_analysable AND days_to_issue < 0""")
    check("no negative review times survive the filter", neg == 0,
          f"{neg:,} negative", "")

    bad_cost = q1(cur, """
SELECT COUNT(*) FROM permits.fact_permits
WHERE cost_is_reported AND (est_const_cost IS NULL OR est_const_cost <= 0)""")
    check("reported costs are positive numbers", bad_cost == 0,
          f"{bad_cost:,} bad", "")

    # ----------------------------------------------- analytical invariants
    fr = q1(cur, f"""
SELECT COUNT(*) FROM permits.fact_permits f
JOIN permits.dim_date da ON da.date_key = f.application_date_key
WHERE {FAIR_WHERE}""")
    check("fair-window record count stable", fr == BASE["fair_records"],
          f"{fr:,} (baseline {BASE['fair_records']:,})", "")

    fp = q1(cur, f"""
SELECT COUNT(DISTINCT f.permit_num) FROM permits.fact_permits f
JOIN permits.dim_date da ON da.date_key = f.application_date_key
WHERE {FAIR_WHERE}""")
    check("fair-window permit count stable", fp == BASE["fair_permits"],
          f"{fp:,} (baseline {BASE['fair_permits']:,})", "")

    for yr, key in [(2017, "median_2017"), (2022, "median_2022"), (2025, "median_2025")]:
        m = float(median_for_year(cur, yr))
        check(f"median {yr} unchanged", abs(m - BASE[key]) < 0.05,
              f"{m} days (baseline {BASE[key]})",
              "A headline figure moved. Re-check the write-up before it is quoted.")

    # The shape of the finding, not just the numbers. This is the check that
    # matters most: it asserts the STORY still holds, not only the values.
    m17, m22, m25 = (float(median_for_year(cur, y)) for y in (2017, 2022, 2025))
    check("finding A shape holds (rose to 2022, then recovered)",
          m22 > m17 and m25 <= m17,
          f"2017={m17} -> 2022={m22} -> 2025={m25}",
          "This is the project's central claim. If the shape inverts, the "
          "conclusion is wrong regardless of whether individual numbers moved.")

    # Censoring must still be visible, or the correction is no longer justified.
    pct26 = q1(cur, """
SELECT ROUND(100.0*AVG(CASE WHEN f.days_to_admin_close<=365 THEN 1 ELSE 0 END),1)
FROM permits.fact_permits f
JOIN permits.dim_date da ON da.date_key = f.application_date_key
WHERE f.is_review_analysable AND da.year = 2026""")
    check("censoring still evident in the latest year",
          pct26 is not None and float(pct26) > 95,
          f"{pct26}% of 2026 permits closed within a year",
          "Below ~95% the censoring argument weakens and the fair-window "
          "correction would need re-justifying.")

    # ------------------------------------------------------------- report
    con.close()
    width = 52
    print("\n" + "=" * 76)
    print("QA REVIEW — Toronto permit review-time analysis")
    print("=" * 76)
    for name, ok, detail, _ in results:
        print(f"  [{'PASS' if ok else 'FAIL'}]  {name:<{width}} {detail}")

    failed = [r for r in results if not r[1]]
    print("-" * 76)
    print(f"  {len(results) - len(failed)} passed, {len(failed)} failed")
    print("=" * 76)

    if failed:
        print("\nWHY EACH FAILURE MATTERS\n")
        for name, _, detail, why in failed:
            print(f"  {name}")
            print(f"    observed: {detail}")
            if why:
                print(f"    {why}")
            print()
        if "--explain" in sys.argv:
            explain([f[0] for f in failed])
        print("Analysis should not be republished until these are explained.\n")
        sys.exit(1)

    print("\nEvery invariant holds. The findings are safe to quote as written.\n")


def explain(names):
    """Optional CLOUD step. Receives only the NAMES of failed checks -
    no data, no rows, no numbers. It writes a paragraph for a non-technical
    reader. It does not decide whether anything passed."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("  (--explain needs ANTHROPIC_API_KEY; the verdicts above stand "
              "without it)\n")
        return
    try:
        import anthropic
        msg = anthropic.Anthropic(api_key=key).messages.create(
            model="claude-sonnet-4-5", max_tokens=300,
            messages=[{"role": "user", "content":
                       "These automated data-quality checks failed on a City of Toronto "
                       "building-permit analysis: " + ", ".join(names) +
                       ". In three sentences of plain English, explain to a non-technical "
                       "manager what may have gone wrong and what to do next. Invent no "
                       "numbers."}])
        print("  PLAIN-LANGUAGE SUMMARY\n")
        print("   ", msg.content[0].text.strip().replace("\n", "\n    "), "\n")
    except Exception as e:
        print(f"  (--explain unavailable: {type(e).__name__})\n")


if __name__ == "__main__":
    main()
