#!/usr/bin/env python3
"""
ask_the_data.py — plain-English questions about Toronto permit review times.

ARCHITECTURE, AND WHY IT IS THIS WAY
------------------------------------
The obvious build is: hand the question and the data to a language model and
let it answer. That design can fabricate numbers, and it fabricates them in
fluent, confident prose, which is the worst possible failure mode for an
analyst tool.

This one is built so that it *cannot*:

    question
       |
       v
  [LOCAL] intent match  ->  a named, pre-written, reviewed SQL query
       |
       v
  [LOCAL] PostgreSQL     ->  the actual numbers
       |
       v
  [CLOUD] language model ->  phrasing ONLY, over numbers it was handed
       |
       v
  answer + the exact SQL that produced it

The model never sees the database and never computes anything. It receives a
small block of already-computed facts and writes two sentences about them. If
the cloud call fails or no API key is present, the tool prints the verified
facts and stops — degraded, never wrong.

Every answer ships with the SQL that produced it, so any figure can be checked.

WHERE THE LOCAL/CLOUD BOUNDARY SITS
-----------------------------------
Local, always:  the permit data, the database, every query, every calculation.
Cloud, only:    (a) matching a question to one of the named queries, and
                (b) phrasing a result from numbers already computed.

For this project the data is public open data, so the boundary is a design
choice rather than a requirement. It is built this way because the same tool
pointed at confidential business data must not leak it — and retrofitting that
boundary later is how leaks happen.

ACHIEVE ASSESSMENT (per the project charter)
--------------------------------------------
A - Aiding coordination   YES. Turns a stakeholder's vague question into a
                          named metric with a stated definition.
C - Cutting tedium        YES. Removes re-deriving the same aggregate by hand.
H - Safety net            PARTIAL. It shows its SQL, which lets a human check
                          it. It does not check itself.
I - Better problem-solving YES. Suggests the adjacent question after each
                          answer.
E - Scaling               YES. One reviewed query serves everyone, instead of
                          each analyst writing their own slightly different one.

Four of five. AI earns its place here.

USAGE
    python ai/ask_the_data.py "is permit review getting faster or slower?"
    python ai/ask_the_data.py --list
"""

import os
import re
import sys
import textwrap

try:
    import psycopg2
except ImportError:
    sys.exit("psycopg2 not installed. pip install psycopg2-binary")

DB = dict(dbname="toronto_permits", user="root", host="/var/run/postgresql")

FAIR = """
  AND f.is_review_analysable
  AND f.days_to_admin_close BETWEEN 0 AND 365
  AND da.year BETWEEN 2017 AND 2025
"""
JOINS = """
FROM permits.fact_permits f
JOIN permits.dim_date da        ON da.date_key       = f.application_date_key
JOIN permits.dim_permit_type t  ON t.permit_type_key = f.permit_type_key
JOIN permits.dim_geography g    ON g.geography_key   = f.geography_key
WHERE 1=1
"""

# ---------------------------------------------------------------------------
# The whole safety model rests on this dictionary. Every query here was written
# and reviewed by a human. The model picks between them; it never writes SQL.
# ---------------------------------------------------------------------------
QUERIES = {
    "trend": {
        "asks": ["trend", "faster", "slower", "improving", "worse", "over time",
                 "by year", "getting better", "deteriorat"],
        "question": "Is permit review getting faster or slower over time?",
        "sql": f"""
SELECT da.year AS application_year,
       COUNT(*) AS records,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.days_to_issue)::numeric,1) AS median_days,
       ROUND(100.0*AVG(CASE WHEN f.days_to_issue<=30 THEN 1 ELSE 0 END),1) AS pct_within_30d
{JOINS}{FAIR}
GROUP BY 1 ORDER BY 1""",
        "caveat": "Like-for-like basis. 2026 excluded: only fast-closing permits "
                  "are in the file yet, which makes recent years look artificially good.",
        "next": "Does the pattern hold inside a single permit type, or is it a mix effect?",
    },
    "district": {
        "asks": ["district", "area", "region", "where", "neighbourhood",
                 "neighborhood", "east", "west", "north", "south", "location"],
        "question": "Does review time depend on which part of the city you build in?",
        "sql": f"""
SELECT g.district_name,
       COUNT(*) AS records,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.days_to_issue)::numeric,1) AS median_all,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.days_to_issue)
             FILTER (WHERE t.permit_type='Small Residential Projects')::numeric,1) AS median_simple,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.days_to_issue)
             FILTER (WHERE t.permit_type='New Houses')::numeric,1) AS median_complex
{JOINS}{FAIR}
GROUP BY 1 ORDER BY median_all DESC""",
        "caveat": "median_all mixes different permit types per district, so it "
                  "overstates the gap. The simple/complex columns are the fair comparison.",
        "next": "Is the complex-permit gap large enough to justify moving reviewer capacity?",
    },
    "cost": {
        "asks": ["cost", "expensive", "price", "value", "budget", "big project",
                 "large project", "$", "dollar"],
        "question": "Do bigger projects wait longer?",
        "sql": f"""
SELECT CASE WHEN f.est_const_cost <   25000 THEN 'A under $25k'
            WHEN f.est_const_cost <  100000 THEN 'B $25k-100k'
            WHEN f.est_const_cost <  500000 THEN 'C $100k-500k'
            WHEN f.est_const_cost < 5000000 THEN 'D $500k-5M'
            ELSE 'E over $5M' END AS cost_band,
       COUNT(*) AS records,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.days_to_issue)::numeric,1) AS median_days,
       ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY f.days_to_issue)::numeric,0) AS p90_days
{JOINS}{FAIR}
  AND t.permit_family='Building' AND f.cost_is_reported AND f.est_const_cost>0
GROUP BY 1 ORDER BY 1""",
        "caveat": "Building permits only. Trade permits do not report a construction "
                  "cost (87-95% placeholder), so including them would be meaningless.",
        "next": "What distinguishes the over-$5M projects that clear quickly from those that stall?",
    },
    "type": {
        "asks": ["type", "kind of permit", "plumbing", "mechanical", "demolition",
                 "new house", "which permit", "category"],
        "question": "Which permit types are slowest?",
        "sql": f"""
SELECT t.permit_type, t.permit_family,
       COUNT(*) AS records,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.days_to_issue)::numeric,1) AS median_days,
       ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY f.days_to_issue)::numeric,0) AS p90_days
{JOINS}{FAIR}
GROUP BY 1,2 HAVING COUNT(*) >= 500 ORDER BY median_days DESC""",
        "caveat": "Types with fewer than 500 records are suppressed as unstable.",
        "next": "Is a slow type slow everywhere, or only in certain districts?",
    },
    "quality": {
        "asks": ["quality", "wrong", "missing", "dirty", "problem", "error",
                 "trust", "reliable", "clean"],
        "question": "What is wrong with this data?",
        "sql": """
SELECT 'source rows'                    AS issue, COUNT(*)::bigint AS rows FROM permits.fact_permits
UNION ALL SELECT 'distinct permits',    COUNT(DISTINCT permit_num) FROM permits.fact_permits
UNION ALL SELECT 'row-count overstatement', COUNT(*)-COUNT(DISTINCT permit_num) FROM permits.fact_permits
UNION ALL SELECT 'cost field = placeholder string', COUNT(*) FILTER (WHERE cost_is_sentinel) FROM permits.fact_permits
UNION ALL SELECT 'never issued',        COUNT(*) FILTER (WHERE flag_never_issued) FROM permits.fact_permits
UNION ALL SELECT 'issued before applied', COUNT(*) FILTER (WHERE flag_issued_before_applied) FROM permits.fact_permits
UNION ALL SELECT 'date in the future',  COUNT(*) FILTER (WHERE flag_future_date) FROM permits.fact_permits
UNION ALL SELECT 'unknown district code', COUNT(*) FILTER (WHERE flag_unknown_district) FROM permits.fact_permits""",
        "caveat": "Found during profiling, before any metric was calculated. "
                  "None of these produced an error message.",
        "next": "Which of these would change a published number if left unhandled?",
    },
    "censoring": {
        "asks": ["censor", "bias", "artifact", "misleading", "why is the trend",
                 "survivor", "why 2026", "closed"],
        "question": "Why can't the raw trend be trusted?",
        "sql": f"""
SELECT da.year AS application_year,
       COUNT(*) AS records,
       ROUND(100.0*AVG(CASE WHEN f.days_to_admin_close<=365 THEN 1 ELSE 0 END),1) AS pct_closed_within_1yr,
       MAX(f.days_to_issue) AS longest_review_in_file
FROM permits.fact_permits f
JOIN permits.dim_date da ON da.date_key = f.application_date_key
WHERE f.is_review_analysable AND da.year BETWEEN 2017 AND 2026
GROUP BY 1 ORDER BY 1""",
        "caveat": "pct_closed_within_1yr rising to 100% is the proof: recent years "
                  "can only contain permits that closed fast.",
        "next": "How would you estimate the true recent figure, given the open permits are invisible?",
    },
}


def pick_query(question: str):
    """LOCAL intent matching. Deterministic, inspectable, no model involved.

    Deliberately simple: scoring keyword overlap is auditable, and a wrong match
    here is visible to the user (the query name and SQL are both printed). A
    model could match better, but it could also match silently wrongly.
    """
    q = question.lower()
    scores = {k: sum(1 for kw in v["asks"] if kw in q) for k, v in QUERIES.items()}
    best = max(scores, key=scores.get)
    return (best, scores[best]) if scores[best] else (None, 0)


def run(sql):
    with psycopg2.connect(**DB) as con, con.cursor() as cur:
        cur.execute(sql)
        return [d[0] for d in cur.description], cur.fetchall()


def as_table(cols, rows):
    w = [max(len(str(c)), max((len(str(r[i])) for r in rows), default=0))
         for i, c in enumerate(cols)]
    line = "  ".join("-" * x for x in w)
    out = ["  ".join(str(c).ljust(w[i]) for i, c in enumerate(cols)), line]
    out += ["  ".join(str(v).ljust(w[i]) for i, v in enumerate(r)) for r in rows]
    return "\n".join(out)


def narrate(question, spec, cols, rows):
    """CLOUD step. Receives only already-computed numbers.

    The prompt forbids arithmetic and forbids figures not present in the data
    block. This is a guardrail, not a guarantee - which is exactly why the SQL
    and the raw table are printed alongside the narrative, every time.
    """
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import anthropic
    except ImportError:
        return None

    facts = as_table(cols, rows)
    prompt = f"""You are summarising a completed analysis for a city operations manager.

QUESTION: {question}

VERIFIED RESULTS (computed in SQL, already checked):
{facts}

MANDATORY CAVEAT: {spec['caveat']}

Rules, absolute:
- Use ONLY numbers that appear in the results above. Do not compute new ones,
  including differences, percentages or averages not shown.
- If a number is not above, say the data does not show it.
- State associations as associations. Claim no cause.
- Two or three sentences. Plain language. No preamble.
- Include the caveat in your own words."""
    try:
        msg = anthropic.Anthropic(api_key=key).messages.create(
            model="claude-sonnet-4-5", max_tokens=320,
            messages=[{"role": "user", "content": prompt}])
        return msg.content[0].text.strip()
    except Exception as e:
        return f"[cloud synthesis unavailable: {type(e).__name__}]"


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return
    if sys.argv[1] == "--list":
        print("\nQuestions this tool can answer:\n")
        for k, v in QUERIES.items():
            print(f"  {k:<11} {v['question']}")
        print()
        return

    question = " ".join(sys.argv[1:])
    name, score = pick_query(question)

    print("=" * 74)
    print(f"Q: {question}")
    print("=" * 74)

    if not name:
        print("\nNo reviewed query matches that question.\n")
        print("This tool answers only from a fixed set of human-written queries.")
        print("It will not improvise SQL, because an improvised query that looks")
        print("right and is subtly wrong is worse than no answer.\n")
        print("Try one of:\n")
        for k, v in QUERIES.items():
            print(f"  {k:<11} {v['question']}")
        print()
        return

    spec = QUERIES[name]
    print(f"\n[LOCAL]  matched query '{name}' (score {score})")
    print(f"[LOCAL]  {spec['question']}")
    cols, rows = run(spec["sql"])
    print(f"[LOCAL]  {len(rows)} rows returned from PostgreSQL\n")
    print(as_table(cols, rows))

    print(f"\nCAVEAT: {textwrap.fill(spec['caveat'], 70, subsequent_indent='        ')}")

    story = narrate(question, spec, cols, rows)
    if story:
        print("\n[CLOUD]  summary, written from the verified numbers above:\n")
        print(textwrap.fill(story, 74, initial_indent="  ", subsequent_indent="  "))
    else:
        print("\n[CLOUD]  skipped - no ANTHROPIC_API_KEY set.")
        print("         The verified numbers above are the answer; the cloud step")
        print("         only rephrases them, so nothing is lost but the prose.")

    print(f"\n[NEXT]   {spec['next']}")
    print("\n" + "-" * 74)
    print("SQL that produced the numbers above:")
    print("-" * 74)
    print(spec["sql"].strip())
    print()


if __name__ == "__main__":
    main()
