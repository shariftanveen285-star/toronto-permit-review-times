# Summary — Toronto Building Permit Review Times

**The question:** How long does Toronto take to approve a building permit, is it
getting better or worse, and what changes the answer?

**Why it matters:** while an applicant waits, they are paying for land, loans,
and sometimes a crew standing idle. "How long is the wait and is it getting
worse" is a question with real money attached.

**Data:** City of Toronto Open Data — Cleared Building Permits since 2017.
438,949 records, applications from 1979 to 2026. Extracted 2026-09-20,
md5 `d5f431c2522692932fbb6040c39ccf54`.

**Metric:** calendar days from application to issue. Median, not mean — the
p90 is roughly four times the median, so a mean describes nobody's real wait.

---

## Finding A — Review times got 45% worse, then fully recovered

**The raw data says the opposite.** Taken at face value it shows steady
improvement from 26 days in 2017 to 8 days in 2026 — a 69% speed-up.

That reading is wrong, and the reason is structural.

**This file contains only permits the City has already closed.** A recent
permit can appear only if it was approved *and* closed quickly, so recent years
hold a survivor sample of fast permits. Two proofs:

| Application year | % closed within 1 year | Longest review present in file |
|---|---|---|
| 2017 | 51.6% | 3,409 days |
| 2024 | 69.5% | 877 days |
| 2025 | 90.6% | 573 days |
| 2026 | **100.0%** | **208 days** |

The longest review a year can contain tracks how long ago that year was, not
anything the City did.

**Applying one closure rule to every year** (issued-to-closed within 365 days)
gives the real trend:

| Year | Median days | | Year | Median days |
|---|---|---|---|---|
| 2017 | 20 | | 2022 | **29 — worst** |
| 2018 | 19 | | 2023 | 27 |
| 2019 | 21 | | 2024 | 20 |
| 2020 | 22 | | 2025 | **18** |
| 2021 | 24 | | | |

n = 145,326 records.

**Tested, not eyeballed:**

| Hypothesis | Test | Result |
|---|---|---|
| 2022 slower than 2017 | Mann-Whitney U | p = 3.6 × 10⁻¹⁴⁰ · +9 days (+45%) |
| 2025 faster than 2022 | Mann-Whitney U | p = 7.1 × 10⁻¹⁴⁸ |
| 2025 differs from 2017 | Mann-Whitney U, two-sided | **p = 0.807 — no difference** |

Mann-Whitney rather than a t-test because the distribution is skewed.

**Read:** performance deteriorated materially through 2022 and has since
returned to its 2017 baseline. The recovery is complete, not partial.

**Association, not cause.** The 2021–22 peak coincides with pandemic
disruption, but this dataset has no staffing, workload or department fields.
The cause cannot be tested here and is not claimed.

---

## Finding B — Districts differ only on complex work

Raw figures suggest East Toronto is 65% slower than South (38 days vs 23).
Holding permit type constant:

| Permit type | South | North | East | West |
|---|---|---|---|---|
| Small Residential Projects | 15 | 15 | 15 | **20** |
| Building Additions/Alterations | 28 | 31 | 35 | 34 |
| New Houses | 30.5 | 35 | 47.5 | **50** |

South vs East on simple permits: identical medians, effect size +0.031 —
detectable only because n = 17,413, and practically meaningless.

**Read:** three of four districts process simple permits at exactly the same
speed. The gap opens on complex work and widens with complexity. West is the
exception, running slower across the board.

**The actionable version:** not "East is slow" but *"complex-permit review
diverges by district while simple permits do not"* — which points at reviewer
capacity for complex files, not at a district's general competence.

---

## Finding C — Cost predicts review time, monotonically

Building permits only (trade permits do not report a construction cost).
n = 38,676. Spearman ρ = +0.192, p ≈ 0.

| Cost band | Median days | Slowest 10% |
|---|---|---|
| under $25k | 17 | 90 |
| $25k–100k | 20 | 85 |
| $100k–500k | 28 | 86 |
| $500k–5M | 34 | 112 |
| over $5M | **51** | **1,036** |

Every step up in cost adds review time. The striking figure is the tail: among
projects over $5M the slowest 10% wait about **three years**, while the median
is 51 days. Most large projects move reasonably; a minority stall badly.

ρ = 0.192 is weak. Cost is a real but partial signal — stated plainly rather
than dressed up.

---

## Data quality — published, not hidden

Every issue below was found before any metric was calculated. **None produced
an error message.**

| Issue | Rows | Consequence if missed |
|---|---|---|
| Permit number not unique | 45,428 extra | Counting rows overstates permits by 11.5% |
| Cost field holds a placeholder string | 222,734 (50.7%) | Cost analysis silently invalid for trade permits |
| Comma-formatted cost values | 51,949 | A plain numeric cast deletes a quarter of usable cost data |
| Completion date is a filing date | all | Read as build time, it is wrong by decades |
| Never issued | 34,702 | No review duration exists; must be excluded |
| Issued before applied | 21 | Impossible sequence |
| Date in the future | 3 | Max 2028-11-03 |
| NULL geography key | 5 | Dropped from every inner join — found by automated QA, not by eye |

The placeholder string, verbatim: `DO NOT UPDATE OR DELETE THIS INFO FIELD`.
A note between City staff, published in a currency column.

---

## Recommendations

1. **Never report this dataset's trend without the closure correction.** The
   uncorrected series says the opposite of the truth. `dashboard/` leads with
   this warning for that reason.
2. **Target complex-permit review in East and West.** That is where the
   dispersion is, and simple permits show it is not a district-wide capacity
   problem.
3. **Investigate the large-project tail, not its median.** A median of 51 days
   against a p90 of 1,036 says a minority of large files stall for years. The
   median is fine; the variance is the problem.
4. **Ask the City for permit status history.** The single field that would
   unlock causation is a hold/resubmission log. Without it, "why" is untestable.
5. **Re-run `ai/qa_reviewer.py` on every refresh.** It already caught one
   structural defect that three rounds of manual review missed.

---

## What this project demonstrates

| Skill | Evidence |
|---|---|
| SQL | Star schema, 5 tables, analysis views, documented RI decisions, an Unknown member |
| Python | Executed analysis with real hypothesis tests; a production pipeline with gates |
| Excel | 107,380 live formulas, zero errors, INDEX/MATCH and COUNTIFS throughout |
| Power Query | Documented Applied Steps + reproducible M code |
| Power BI | Full rebuild spec: data model, DAX, visual-to-field mapping, theme, verification table |
| Data cleansing | 8 distinct defects found, classified and handled — none by deletion |
| Statistics | Correct test for the distribution; effect size reported beside every p-value |
| Communication | This summary, a plain-English companion, a public dashboard, a visual mental model |
| AI fluency | Local/cloud boundary by design; AI phrases and checks, never computes |
| Judgement | Two headline conclusions overturned by testing the obvious answer |

**The single most important thing in this repo:** the first answer was wrong,
twice, and the work that proved it is written down.
