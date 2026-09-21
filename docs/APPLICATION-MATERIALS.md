# Application Materials

Tailored to *Reporting & Data Analyst (SQL / Python / Power BI)*, Collection nc
— https://to.indeed.com/aafhwxldrd7j

Everything here is generated from what actually exists in the repo. Nothing is
claimed that cannot be shown.

> **Edit these into your own voice before sending.** They are drafted to be
> accurate, not to sound like you. A cover letter that reads like it was
> written by someone else is worse than a plainer one that sounds like you.

---

## Resume bullets

Pick 4–6. Each maps to a stated requirement in the posting.

**Lead with these three:**

- Analysed 438,949 City of Toronto permit records end to end — Excel/Power
  Query, PostgreSQL star schema, Python, and a published interactive dashboard
  — and **reversed the headline conclusion** by identifying a sampling bias
  that made a 45% decline in performance appear as a 69% improvement.

- Found and documented **five data defects that produced no error message**,
  including a system placeholder string occupying 50.7% of a currency column
  and 52,000 comma-formatted values that a standard numeric conversion deletes
  silently.

- **Cross-validated every headline metric across Excel, SQL and Python**,
  reconciling to four decimal places, and published the reconciliation table
  alongside the analysis.

**Then choose from:**

- Built a PostgreSQL star schema (1 fact, 4 dimensions, 438,949 rows) with
  documented referential-integrity decisions and an Unknown-member pattern that
  eliminated silent row loss across every reporting view.

- Automated a five-stage reporting pipeline with hard validation gates and a
  mandatory human-approval step; built an automated QA agent running 16
  invariants that **caught a structural defect three rounds of manual review
  had missed**.

- Designed a hybrid local/cloud AI layer in which the language model never
  computes a figure — SQL produces every number, the model only phrases
  verified results, and every answer ships with the query that produced it.

- Produced a complete Power BI rebuild specification — data model,
  relationships, every DAX measure, visual-to-field mapping, theme JSON and a
  verification table — so the web dashboard and a native `.pbix` are provably
  equivalent.

- Built an Excel analysis workbook of **107,380 live formulas with zero errors**
  (INDEX/MATCH, COUNTIFS, AVERAGEIFS), recalculated and validated, with every
  derived value driven by formula rather than pasted result.

- Applied non-parametric hypothesis testing (Mann-Whitney U, Kruskal-Wallis,
  Spearman) appropriate to a skewed distribution, and **reported effect sizes
  alongside p-values** — identifying one result significant at p = 2×10⁻¹⁵ whose
  practical difference was zero.

---

## Cover letter — draft

> Dear Hiring Team,
>
> I'm applying for the Reporting & Data Analyst role in Markham.
>
> Your posting says you'll consider demonstrated experience through personal
> projects and GitHub. I'd like to be judged on exactly that, so here is one
> piece of work and what it shows.
>
> I analysed 438,949 City of Toronto building permit records to answer a simple
> question: how long does the City take to approve a permit, and is it getting
> better or worse? The raw data says approvals got 69% faster since 2017. That
> answer is wrong. The dataset only contains permits the City has already
> closed, so recent years only contain the fast ones — 100% of 2026's permits
> closed within a year, because nothing slower could be in the file yet.
>
> Applying one consistent rule to every year reversed the finding: review times
> got 45% *worse* between 2017 and 2022, then recovered completely. I tested it
> rather than asserting it — Mann-Whitney U, because the distribution is
> skewed — and 2025 came back statistically identical to 2017.
>
> Along the way I found four defects that produced no error message. Half the
> construction-cost column contained a note between City staff reading "DO NOT
> UPDATE OR DELETE THIS INFO FIELD". Another 52,000 cost values were written
> with commas, which a standard numeric conversion silently turns into blanks —
> a quarter of the usable data, gone without a warning.
>
> I built the whole pipeline: cleaning in Excel and Power Query with documented
> M code, a PostgreSQL star schema, analysis in Python, an interactive dashboard
> and a full Power BI rebuild specification. Every headline number is computed
> three ways and reconciles to four decimal places.
>
> On the AI side, your posting lists Cursor AI as preferred. I built a tool that
> answers plain-English questions about the data, designed so the model never
> touches the database — SQL computes every figure, the model only phrases what
> it is handed, and every answer prints the query behind it. I also built an
> automated QA checker that found a structural bug three rounds of manual review
> had missed.
>
> My background is in inbound sales, and I'm studying data analytics. I don't
> have an analyst job title yet. What I have is two end-to-end projects where
> the interesting part was catching what the data got wrong.
>
> Repository and dashboard links below. I'd welcome the chance to walk through
> the reasoning.
>
> Thank you for your time,
> Tanveen Sharif

---

## Requirement → evidence, for your own reference

| Their words | Your evidence |
|---|---|
| Strong SQL — joins, aggregations, transformation | `sql/` — star schema, analysis views, documented RI decisions |
| Working knowledge of Python for analysis **and automation** | `python/` — analysis *and* `pipeline.py`. Both halves |
| Experience with Microsoft Excel | 107,380 live formulas, zero errors |
| Power BI | `dashboard/POWERBI_REBUILD.md` — full spec with verification table |
| Data cleansing & validation | `logs/02-dig-describe.md` — 8 defects found, classified, handled |
| Power Query *(preferred)* | `excel/POWER_QUERY_STEPS.md` — Applied Steps + real M code |
| Power Automate *(preferred)* | `python/pipeline.py` + documented equivalent flow design |
| API Integration *(preferred)* | CKAN API sourcing, documented including the egress block hit |
| **Cursor AI** *(preferred)* | `ai/` — hybrid local/cloud layer with ACHIEVE reasoning per component |
| Automate recurring reports | `pipeline.py` — five stages, two hard gates, approval step |
| Investigate data discrepancies | The QA agent, and five defects traced to root cause |
| Document sources, logic, workflows | `logs/00`–`06`, `docs/`, `README.md` |

---

## Before you send

**1. Fix your Indeed profile.** It currently lists ten preferred job titles,
none of them analyst — CRM Coordinator, Administrative Coordinator, Marketing
Assistant and so on. No SQL, no Python, no Power BI in the skills. Right now it
tells Indeed's matching engine you are a sales coordinator, which is probably
costing you more than any single project gains you.

Also: max commute is set to 25 minutes. Toronto to Markham will exceed that,
and it may be filtering these roles out before you ever see them.

**2. Verify the employer.** Collection nc has no Indeed company profile — no
description, reviews, sector or headcount — and no web presence I could find.
Click the apply link and see what employer name appears on the application
form; that usually reveals the real legal entity. Then check it on LinkedIn and
the Ontario Business Registry. Ten minutes, before you invest more.

**3. Push the repo.** The posting explicitly says GitHub portfolios count.
A repo you can link is the single highest-value thing in this application.

**4. Note the salary discrepancy.** The body of the posting says $55,000–60,000;
the structured pay field says $50,000–60,000. Worth a question at interview.
