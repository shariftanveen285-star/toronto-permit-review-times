#!/usr/bin/env python3
"""
pipeline.py — the manual analysis, turned into a program.

WHY THIS EXISTS, AND WHY IT EXISTS *LAST*
-----------------------------------------
The charter is explicit: "Do not automate a process before it has been
understood and validated manually."

So this file was written after the analysis, not before. Every step in it was
first done by hand, checked against two other tools, and only then encoded.
Automating first would have baked in the two errors that manual work caught:
treating COMPLETED_DATE as build time, and throwing away 52,000
comma-formatted cost values.

That ordering is the point. Automation multiplies whatever it is given,
including mistakes.

ACHIEVE ASSESSMENT (per the project charter)
--------------------------------------------
A - Aiding coordination    NO.
C - Cutting tedium         YES. Five manual steps, monthly, forever.
H - Safety net             YES. Gates on qa_reviewer; refuses to publish on
                           a failed check.
I - Better problem-solving NO. It repeats thinking already done.
E - Scaling                YES. This is the reason it exists.

Three of five, and E is emphatic.

WHAT IT DOES

    new CSV
      |
      v
    [1] validate input        schema, row count, encoding      -> HARD GATE
      |
      v
    [2] clean                 the documented rules only
      |
      v
    [3] load                  rebuild the star schema
      |
      v
    [4] QA gate               ai/qa_reviewer.py                 -> HARD GATE
      |
      v
    [5] refresh outputs       dashboard data, Excel extract
      |
      v
    [6] human approval        <- STOPS HERE. Always.

Step 6 is not a placeholder. Nothing in this pipeline publishes anything to a
stakeholder. It prepares, checks, and reports; a person decides. An unattended
process that can publish a wrong number to a manager is not automation, it is
an unexploded liability.

USAGE
    python python/pipeline.py --input data/raw/new_extract.csv
    python python/pipeline.py --input <file> --dry-run
"""

import argparse
import hashlib
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "logs" / "pipeline_runs.log"

EXPECTED_COLUMNS = [
    "_id", "PERMIT_NUM", "REVISION_NUM", "PERMIT_TYPE", "STRUCTURE_TYPE",
    "WORK", "STREET_NUM", "STREET_NAME", "STREET_TYPE", "STREET_DIRECTION",
    "POSTAL", "GEO_ID", "WARD_GRID", "APPLICATION_DATE", "ISSUED_DATE",
    "COMPLETED_DATE", "STATUS", "DESCRIPTION", "CURRENT_USE", "PROPOSED_USE",
    "DWELLING_UNITS_CREATED", "DWELLING_UNITS_LOST", "EST_CONST_COST",
    "ASSEMBLY", "INSTITUTIONAL", "RESIDENTIAL",
    "BUSINESS_AND_PERSONAL_SERVICES", "MERCANTILE", "INDUSTRIAL",
    "INTERIOR_ALTERATIONS", "DEMOLITION", "BUILDER_NAME",
]
MIN_ROWS = 300_000          # a smaller file means a truncated download


class Halt(Exception):
    """A gate refused to open. Never caught - the run stops."""


def log(msg, level="INFO"):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {level:<5}  {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as fh:
        fh.write(line + "\n")


def run(cmd, what, retries=1):
    """Run a step. Retries once on failure, because a transient DB hiccup
    should not require a human, but a real error should surface immediately."""
    for attempt in range(1, retries + 2):
        log(f"{what} (attempt {attempt})")
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if p.returncode == 0:
            return p.stdout
        log(f"{what} failed rc={p.returncode}", "ERROR")
        if p.stderr.strip():
            log(p.stderr.strip()[-600:], "ERROR")
        if attempt <= retries:
            time.sleep(3)
    raise Halt(f"{what} failed after {retries + 1} attempts")


# ------------------------------------------------------------------ step 1
def validate_input(path: Path):
    log("STEP 1 — validating input file")
    if not path.exists():
        raise Halt(f"input not found: {path}")

    size_mb = path.stat().st_size / 1024 ** 2
    h = hashlib.md5(path.read_bytes()).hexdigest()
    log(f"  {path.name}  {size_mb:,.1f} MB  md5={h}")

    with path.open(encoding="utf-8") as fh:
        header = fh.readline().strip().split(",")
        rows = sum(1 for _ in fh)

    missing = [c for c in EXPECTED_COLUMNS if c not in header]
    extra = [c for c in header if c not in EXPECTED_COLUMNS]
    if missing:
        raise Halt(f"schema changed — missing columns: {missing}")
    if extra:
        # Not fatal: the City adding a column does not break anything we use.
        # But it must be seen, because it may mean a redesign upstream.
        log(f"  new columns present (not used): {extra}", "WARN")
    if rows < MIN_ROWS:
        raise Halt(f"only {rows:,} rows (expected >= {MIN_ROWS:,}) — "
                   "likely a truncated download, not a real shrink")

    log(f"  schema OK, {rows:,} data rows")
    return h, rows


# --------------------------------------------------------------- steps 2-5
def clean():
    log("STEP 2 — cleaning (documented rules only)")
    out = run([sys.executable, "python/02_clean.py"], "clean", retries=1)
    for ln in out.splitlines():
        if any(k in ln for k in ("cost:", "fact_permits", "is_review_analysable")):
            log("  " + ln.strip())


def load():
    log("STEP 3 — rebuilding star schema")
    run(["psql", "-q", "-d", "toronto_permits", "-f", "sql/01_schema.sql"],
        "schema rebuild")
    for t in ["dim_date", "dim_geography", "dim_permit_type", "dim_status",
              "fact_permits"]:
        run(["psql", "-q", "-d", "toronto_permits", "-c",
             f"\\copy permits.{t} FROM 'data/processed/{t}.csv' "
             "WITH (FORMAT csv, HEADER true, NULL '')"], f"load {t}")
    run(["psql", "-q", "-d", "toronto_permits", "-f", "sql/02_views.sql"],
        "rebuild views")
    log("  star schema rebuilt")


def qa_gate():
    """HARD GATE. qa_reviewer exits non-zero on any failed invariant."""
    log("STEP 4 — QA gate")
    p = subprocess.run([sys.executable, "ai/qa_reviewer.py"],
                       cwd=ROOT, capture_output=True, text=True)
    for ln in p.stdout.splitlines():
        if "[PASS]" in ln or "[FAIL]" in ln or "passed," in ln:
            log("  " + ln.strip())
    if p.returncode != 0:
        raise Halt("QA gate failed — see output above. Nothing downstream ran.")
    log("  all invariants hold")


def refresh_outputs():
    log("STEP 5 — refreshing outputs")
    run([sys.executable, "python/03_build_excel.py"], "rebuild Excel workbook")
    run([sys.executable, "python/04_validate.py"], "cross-validate three tools")
    log("  outputs refreshed and reconciled")


# ------------------------------------------------------------------ step 6
def approval_summary(h, rows, started):
    mins = (time.time() - started) / 60
    print("\n" + "=" * 76)
    print("READY FOR REVIEW — NOTHING HAS BEEN PUBLISHED")
    print("=" * 76)
    print(f"  source md5     {h}")
    print(f"  rows in        {rows:,}")
    print(f"  runtime        {mins:.1f} min")
    print(f"  run log        logs/pipeline_runs.log")
    print("""
  A human still has to:
    1. read the QA output above
    2. open excel/permit_review_analysis.xlsx and check the Validation tab
    3. re-read logs/00-summary-key-findings.md — do the findings still hold?
    4. only then republish the dashboard

  This pipeline deliberately cannot do step 4. An unattended process that can
  publish a wrong number to a stakeholder is not automation; it is a liability
  with a schedule attached.
""")
    print("=" * 76 + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, help="path to a new source CSV")
    ap.add_argument("--dry-run", action="store_true",
                    help="validate the input only; change nothing")
    a = ap.parse_args()

    started = time.time()
    log("=" * 60)
    log(f"PIPELINE START  input={a.input}  dry_run={a.dry_run}")

    try:
        h, rows = validate_input(Path(a.input))
        if a.dry_run:
            log("dry run — input valid, stopping before any change")
            return 0
        clean()
        load()
        qa_gate()
        refresh_outputs()
        approval_summary(h, rows, started)
        log("PIPELINE COMPLETE — awaiting human approval")
        return 0
    except Halt as e:
        log(str(e), "HALT")
        log("PIPELINE STOPPED. Nothing downstream ran. No output was changed.",
            "HALT")
        return 1
    except Exception as e:                      # noqa: BLE001
        log(f"unexpected {type(e).__name__}: {e}", "ERROR")
        return 2


if __name__ == "__main__":
    sys.exit(main())
