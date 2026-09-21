# Requirement → Evidence Matrix

> The contract between the posting and this repo. Every requirement the
> employer stated gets a named artifact that proves it. Nothing is left to the
> reader's imagination, and nothing in the repo exists without a reason.
>
> Status column: `PLANNED` → `BUILT` → `VALIDATED` (cross-checked) →
> `DEFENSIBLE` (Tan can explain it cold, unaided).

**Target:** Reporting & Data Analyst (SQL / Python / Power BI) — see
`00-target-posting.md`
**Last updated:** 2026-09-20

---

## Required technical skills

| ID | Requirement (their words) | Evidence artifact | Status |
|---|---|---|---|
| T1 | **SQL** — joins, aggregations, data transformation, reporting | `sql/` — star schema DDL, analysis views, documented RI decisions | PLANNED |
| T2 | **Python** — for data analysis *and automation* | `python/` executed notebook (analysis) **+** `python/pipeline.py` (automation). Both halves, because they asked for both. | PLANNED |
| T3 | **Microsoft Excel** | `excel/` live-formula workbook — INDEX/MATCH, AVERAGEIFS/COUNTIFS, IF flags. Recalculated to zero errors. | PLANNED |
| T4 | **Power BI** | Interactive dashboard + `dashboard/POWERBI_REBUILD.md` with exact data model, DAX measures, visual-to-field mapping | PLANNED |
| T5 | **Data Analysis** | `python/` notebook — real hypothesis tests (scipy), not eyeballed charts | PLANNED |
| T6 | **Data Cleansing & Validation** | `logs/03-data-quality.md` — every issue found, what it *meant*, and the decision taken (per DIG-D step 6: do not auto-fix) | PLANNED |

## Preferred technical skills

| ID | Requirement | Evidence artifact | Status |
|---|---|---|---|
| P1 | **Power Query** | `excel/POWER_QUERY_STEPS.md` — documented Applied Steps + real M code, pasteable into Advanced Editor | PLANNED |
| P2 | **Power Automate** | Covered by proxy: `python/pipeline.py` + `logs/07-automation.md` documents the equivalent Power Automate flow design | PLANNED |
| P3 | **API Integration** | Data sourced via a live open-data API rather than a manual CSV download — makes this real, not claimed | PLANNED |
| P4 | **Microsoft SQL Server** | Covered by proxy: PostgreSQL. `sql/README.md` notes T-SQL dialect differences explicitly. | PLANNED |
| P5 | **Cursor AI** | `ai/` — hybrid local/cloud AI layer + `logs/06-ai-layer.md` documenting the ACHIEVE reasoning for every AI use and the local/cloud data boundary | PLANNED |

## Key responsibilities

| ID | Responsibility | Evidence artifact | Status |
|---|---|---|---|
| R1 | Operational, financial, management reports | Dashboard's three-tier structure: KPI row → trends → diagnostics → detail | PLANNED |
| R2 | Extract, clean, transform, analyze in SQL + Python | End-to-end pipeline, every stage logged | PLANNED |
| R3 | Dashboards, scorecards, visualizations | Dashboard + rebuild guide | PLANNED |
| R4 | **Automate recurring reports and manual processes** | `python/pipeline.py` — inputs, outputs, validation, error handling, logging. Built *after* manual validation, per ACHIEVE-E. | PLANNED |
| R5 | **Investigate data discrepancies, maintain data quality** | `logs/03-data-quality.md` + cross-validation reconciliation table (SQL vs Excel vs Python) | PLANNED |
| R6 | Stakeholder translation → actionable insights | `docs/02-stakeholder-brief.md` — the ACHIEVE-A artifact: vague business concern → stakeholder, question, metric, segmentation, next analysis | PLANNED |
| R7 | **Document data sources, reporting logic, automation workflows** | `logs/00`–`07` + `README.md`. This is the traceability mandate from the charter. | PLANNED |
| R8 | Identify process-improvement opportunities | `logs/00-summary-key-findings.md` — recommendations section | PLANNED |
| R9 | Support BI/analytics initiatives | Whole repo | PLANNED |

## Qualifications

| ID | Requirement | How we answer it | Status |
|---|---|---|---|
| Q1 | Diploma / degree **or equivalent practical experience** | Advanced diploma (Seneca) + this repo as practical evidence | MET |
| Q2 | 1–3 years — **project experience will be considered** | RentSafeTO (project 1) + this project (project 2). Two end-to-end pipelines. | PLANNED |
| Q6 | Analytical & problem-solving | The hypothesis that gets **overturned** by a real test — the reversal is the proof | PLANNED |
| Q7 | Attention to detail | Cross-validation table where three tools reconcile to the cent | PLANNED |
| Q8 | Written & verbal communication | `logs/00-summary-key-findings.md` (written) + `INTERVIEW_PREP.md` (verbal) | PLANNED |

---

## Deliberate gaps — stated honestly

| Gap | Why we are not faking it |
|---|---|
| No real MS SQL Server instance | PostgreSQL is used; dialect differences documented. Claiming SQL Server on a resume from a Postgres project is the kind of thing that collapses in a technical screen. |
| No Power BI Desktop licence/install | Equivalent dashboard built, plus an exact rebuild guide. We say so plainly rather than implying a `.pbix` exists. |
| No Power Automate tenant | Flow design documented; Python equivalent built and runnable. |

> **Charter rule in force:** only *personally practiced or genuinely understood*
> work counts as interview-ready evidence. The `DEFENSIBLE` status is not
> granted by Claude — it is granted when Tan explains the artifact unaided.
