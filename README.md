# Toronto Building Permit Review Times

**How long does Toronto take to approve a building permit, and is it getting
better or worse?**

An end-to-end analysis of 438,949 City of Toronto permit records — Excel and
Power Query, PostgreSQL, Python, a published dashboard, and a hybrid
local/cloud AI layer.

**[Live dashboard →](https://claude.ai/artifact/HZUdjZLgVB4JQFjzYrwqrA)**

---

## The finding

The raw data says permit approvals got **69% faster** since 2017, improving
from 26 days to 8.

That is false, and the reason is structural.

This dataset contains only permits the City has **already closed**. A recent
permit appears only if it was approved *and* closed quickly — so recent years
hold a survivor sample of fast permits. Of permits applied for in 2017, 52%
had closed within a year. Of those applied for in 2026, **100%** had, because
nothing slower could yet be in the file.

Applying one identical closure rule to every year reverses the story:

| Year | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|---|
| **Median days** | 20 | 19 | 21 | 22 | 24 | **29** | 27 | 20 | **18** |

Review times got **45% worse** between 2017 and 2022, then recovered
completely. 2025 is statistically indistinguishable from 2017 (Mann-Whitney,
p = 0.807).

Two further findings, both of which also reversed the obvious reading:

- **Districts differ only on complex work.** Raw figures suggest East is 65%
  slower than South. Holding permit type constant, three of four districts
  process simple permits at *identical* speed; the gap appears only as projects
  get more complex.
- **Cost predicts review time monotonically** — 17 days under $25k rising to 51
  days over $5M. But the slowest 10% of large projects wait **1,036 days**,
  about three years.

Full write-up: [`logs/00-summary-key-findings.md`](logs/00-summary-key-findings.md)

---

## Four data defects, none of which threw an error

| Defect | Scale | What it breaks |
|---|---|---|
| Permit number is not unique | 45,428 extra rows | Counting rows overstates permits by 11.5% |
| Cost field holds a staff note — `DO NOT UPDATE OR DELETE THIS INFO FIELD` | 222,734 rows (50.7%) | Missing-not-at-random by permit type; cross-type cost averages are meaningless |
| Cost values written `50,000` with a comma | 51,949 rows | A plain numeric cast silently deletes a quarter of usable cost data |
| `COMPLETED_DATE` is a filing date, not a build date | all rows | Read as construction time, it is wrong by decades — intervals reach 46 years |

A fifth was found later by the automated QA agent: five rows with a NULL
dimension key, silently dropped from every query. Zero impact on the findings;
fixed anyway.

---

## Repository

```
data/raw/          source CSV (438,949 rows, md5 in the logs)
data/processed/    star-schema tables

excel/             live-formula workbook (107,380 formulas, 0 errors)
                   + documented Power Query Applied Steps and M code
sql/               PostgreSQL star schema and analysis views
python/            profiling, cleaning, workbook build, cross-validation,
                   and a gated production pipeline
ai/                plain-English query tool + automated QA reviewer
dashboard/         published dashboard + full Power BI rebuild spec

logs/              one log per stage, written as it happened
docs/              target posting, requirement matrix, decisions,
                   plain-English companion
tutor/             the concepts behind each stage, taught from scratch
INTERVIEW_PREP.md  pitch, numbers, and likely questions with answers
```

## Running it

```bash
pip install pandas scipy psycopg2-binary openpyxl
service postgresql start

python python/01_profile.py                 # DIG: Describe — find, do not fix
python python/02_clean.py                   # apply the documented rules
psql -d toronto_permits -f sql/01_schema.sql
# ...load data/processed/*.csv, then:
psql -d toronto_permits -f sql/02_views.sql

python python/03_build_excel.py             # build the workbook
python python/04_validate.py                # reconcile Excel vs SQL vs Python
python ai/qa_reviewer.py                    # 16 invariants — exits 1 on failure

python ai/ask_the_data.py "is review getting faster or slower?"
python python/pipeline.py --input <new.csv> --dry-run
```

---

## Method

Two frameworks govern the work, defined in
[`docs/operating-charter`](docs/) and applied throughout:

**DIG** structures the analysis — *Describe* the data before calculating
anything, *Introspect* for patterns worth testing, then *Goal-set* around the
decision the analysis must support. Every one of the four defects above was
found during Describe, before a single metric existed.

**ACHIEVE** decides where AI belongs. Each AI component carries its own
assessment in its file header, and one candidate — a chatbot over the data —
was rejected for failing the gate.

Standing rules, visible in the code:

- **Flag, never delete.** Every source row survives into the fact table with
  quality flags. Filtering happens in views, where it is visible and reversible.
- **Cross-validate.** Every headline number computed three ways. They reconcile
  to four decimal places; if they hadn't, the analysis would have stopped.
- **Automate last.** `pipeline.py` was written after the manual work, because
  automating first would have encoded the two errors manual work caught.
- **AI phrases, never computes.** Every number in this repo came from SQL,
  Excel or pandas.

---

## Honest limitations

- The closure correction reduces the sampling bias; it does not eliminate it.
- **Causation is untestable here.** No staffing, workload, reviewer or
  hold-reason field exists. The 2021–22 deterioration coincides with pandemic
  disruption, but this data cannot test that, and the write-up says so.
- Cost analysis covers building permits only — trade permits do not report a
  construction cost.
- `BUILDER_NAME` is 95.1% null, so supplier performance is out of scope.
- No Microsoft SQL Server instance and no Power BI Desktop licence were
  available. PostgreSQL was used with dialect differences documented, and the
  dashboard ships with an exact Power BI rebuild specification rather than a
  `.pbix`.

---

## Source

City of Toronto Open Data — *Cleared Building Permits since 2017*
CKAN resource `a96c0ba4-3026-402b-b09d-5b1268b8f810` · extracted 2026-09-20
Licence: [Open Government Licence – Toronto](https://open.toronto.ca/open-data-license/)
