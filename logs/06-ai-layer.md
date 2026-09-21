# Log 06 — The AI layer

Three components. Each was put through the charter's ACHIEVE gate before being
built, and each header carries its own assessment so the reasoning travels with
the code.

**The rule that shaped all three:** *do not add AI to make the project look
advanced.* The easy version of this stage is a chatbot over the data. That
would have failed the gate and would have been the most dangerous thing in the
repo.

---

## Component 1 — `ai/ask_the_data.py`

Plain-English questions about permit review times.

### ACHIEVE — 4 of 5

| | Verdict |
|---|---|
| **A** Aiding coordination | YES — turns a vague stakeholder question into a named metric with a stated definition |
| **C** Cutting tedium | YES — removes re-deriving the same aggregate by hand |
| **H** Safety net | PARTIAL — it shows its SQL so a human can check it; it does not check itself |
| **I** Better problem-solving | YES — proposes the adjacent question after every answer |
| **E** Scaling | YES — one reviewed query serves everyone |

### The architecture, and the failure it is built to prevent

The obvious build is: give the question and the data to a language model, let
it answer. **That design fabricates numbers, in fluent and confident prose** —
the worst available failure mode for an analyst tool, because the output looks
exactly like a correct answer.

This one is built so that it cannot:

```
question
   │
   ▼
[LOCAL]  keyword intent match → a named, human-written, reviewed SQL query
   │
   ▼
[LOCAL]  PostgreSQL computes the numbers
   │
   ▼
[CLOUD]  language model writes 2-3 sentences over numbers it was handed
   │
   ▼
answer + the exact SQL that produced it
```

The model never sees the database, never writes SQL, and never calculates.
It receives a small block of already-computed facts and phrases them.

Four specific guards:

1. **Six reviewed queries, no improvisation.** Ask something outside the set
   and it refuses and lists what it can answer. A generated query that looks
   right and is subtly wrong is worse than no answer.
2. **The prompt forbids arithmetic** and forbids any figure not present in the
   supplied block. A guardrail, not a guarantee — which is why (3) exists.
3. **Every answer prints the SQL that produced it.** Any figure is checkable in
   ten seconds.
4. **Degrades, never guesses.** No API key → prints the verified numbers and
   says the cloud step was skipped. Nothing is lost but the prose.

Each query also carries a mandatory caveat that is passed to the model and
printed regardless — so the censoring warning cannot be dropped from an answer
about the trend.

### Intent matching is deliberately dumb

Keyword overlap, not a model. A model would match better. But a wrong match
here is *visible* — the query name and its SQL are both printed — whereas a
model's wrong match would be silent and confident. For a routing decision this
cheap, auditable beats accurate.

---

## Component 2 — `ai/qa_reviewer.py`

Sixteen invariants, run as assertions.

### ACHIEVE — 3.5 of 5

| | Verdict |
|---|---|
| **A** Aiding coordination | NO |
| **C** Cutting tedium | YES — re-checking 16 invariants by hand takes an hour, and is exactly the job people quietly stop doing |
| **H** Safety net | YES — this is the entire purpose |
| **I** Better problem-solving | PARTIAL — says what broke, not why |
| **E** Scaling | YES — runs on every refresh, unattended |

### Almost none of it is a language model, on purpose

A data-quality check must be deterministic. Asking a model "does this look
right?" gives a different answer on a different day, which is the opposite of
what a check is for.

AI's actual contribution was **writing** the checks — turning a human's list of
"things that must stay true" into executable assertions. That is ACHIEVE-C,
cutting tedium, and the human still owns the list.

The optional `--explain` flag sends only the **names** of failed checks to a
model for a plain-language summary. No data, no rows, no numbers. The verdicts
themselves are arithmetic.

**An AI that grades its own homework is not a safety net.**

### What it checks

Structural (5): row count, distinct permits, fan-out still present, no orphaned
dimension keys, surrogate key unique.

Quality (4): sentinel count stable, contradictory flags, negative durations,
cost sign.

Analytical (7): fair-window counts, the three headline medians, **the shape of
Finding A**, and whether censoring is still evident.

That shape check is the one that matters most. It asserts the *story* still
holds — rose to 2022, recovered by 2025 — not merely that individual numbers
are unchanged. A finding can invert while every number stays within tolerance.

---

## It immediately caught a real defect

First run: **15 passed, 1 failed.**

```
[FAIL]  no orphaned dimension keys        5 orphans
```

Five fact rows had a NULL `geography_key`. Every view in `sql/02_views.sql`
inner-joins `dim_geography` — so those five rows were being silently dropped
from every query. No error. No warning. A total that is quietly short.

**Traced:** five permits, all type `AS Alternative Solution`, all `Cancelled`,
all with no `WARD_GRID` in the source. `dim_geography` was built by dropping
nulls, so there was no row for them to join to.

**Impact on the findings: zero.** All five are non-analysable (cancelled
permits have no review duration), so none reached any published figure.

**Fixed anyway.** `dim_geography` now carries an explicit **Unknown member**
(`geography_key = 0`), and unmatched facts map to it instead of to NULL. This
is the standard dimensional-modelling answer: unmatched facts still join, and
their unknown-ness becomes visible rather than invisible.

After the fix: **16 passed, 0 failed.**

### Why fix something with zero impact

Because the impact was zero *this month*. The structure was wrong. Next
refresh, the unmatched rows might not all be cancelled — and the failure mode
is silent undercounting, which is the kind nobody notices until a stakeholder
does.

This is also the honest answer to "what does your AI layer actually do?" It
found a bug a human review missed, in a repo that had already been checked
three ways.

---

## Component 3 — `python/pipeline.py`

The manual analysis, turned into a program.

### ACHIEVE — 3 of 5, and E is emphatic

| | Verdict |
|---|---|
| **A** Aiding coordination | NO |
| **C** Cutting tedium | YES — five manual steps, monthly, forever |
| **H** Safety net | YES — gates on `qa_reviewer`, refuses to continue on failure |
| **I** Better problem-solving | NO — repeats thinking already done |
| **E** Scaling | YES — the reason it exists |

### It was written last, and that is the point

The charter: *do not automate a process before it has been understood and
validated manually.*

Automating first would have encoded the two errors that manual work caught —
treating `COMPLETED_DATE` as build time, and discarding 52,000 comma-formatted
cost values. **Automation multiplies whatever it is given, mistakes included.**

```
new CSV → [1] validate input ─── HARD GATE
        → [2] clean
        → [3] rebuild star schema
        → [4] QA gate ─────────── HARD GATE
        → [5] refresh outputs
        → [6] human approval ──── STOPS HERE, ALWAYS
```

### Gates tested, not assumed

| Test | Result |
|---|---|
| Valid file, dry run | Passed — schema OK, 438,949 rows, md5 logged |
| Truncated file (4,999 rows) | **HALTED** — "likely a truncated download, not a real shrink" |
| Missing `EST_CONST_COST` column | **HALTED** — "schema changed — missing columns" |

A new column that we do not use logs a WARN and continues — the City adding a
field should not stop the pipeline, but it must be seen.

### Step 6 is not a placeholder

Nothing in this pipeline publishes anything to a stakeholder. It prepares,
checks and reports; a person decides. The approval summary tells them exactly
what to read before republishing, and states plainly that the pipeline cannot
do it for them.

*An unattended process that can publish a wrong number to a manager is not
automation. It is a liability with a schedule attached.*

---

## The local / cloud boundary, stated explicitly

| Stage | Where | Why |
|---|---|---|
| Source data | **Local** | Never transmitted |
| All queries and calculations | **Local** | Determinism and auditability |
| QA verdicts | **Local** | Pure arithmetic |
| Intent matching | **Local** | Auditable beats accurate for cheap routing |
| Phrasing a result | **Cloud** | Receives only already-computed numbers |
| Explaining failed check *names* | **Cloud** | Receives names only — no data |

For this project the data is public open data, so the boundary is a design
choice rather than a requirement.

**It is built this way anyway**, because the same tool pointed at confidential
business data must not leak it — and a boundary retrofitted later is how leaks
happen. The architecture is the control, not a policy document.

---

## Relevance to the target posting

The posting lists **Cursor AI** under preferred technical skills, and names
"automate recurring reports and manual business processes" and "investigate
data discrepancies" among the responsibilities.

- `ask_the_data.py` → AI applied to analysis without surrendering accuracy
- `qa_reviewer.py` → investigating data discrepancies, automatically, forever
- `pipeline.py` → automating a recurring process, with approval gates

What this layer is **not** is a demonstration that AI can replace the analysis.
Every number in this repo was computed by SQL, Excel or pandas, cross-checked
across all three, and reconciled to four decimal places. The AI layer routes,
checks, phrases and schedules. It does not decide.
