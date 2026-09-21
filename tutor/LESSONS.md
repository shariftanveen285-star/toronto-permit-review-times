# The Concepts, Taught From Scratch

Every idea this project uses, explained in plain words, with the real example
from the data and a question to test yourself on.

Read it before an interview. Work the questions without looking.

---

# STAGE 1 — SOURCING

## Grain

**What it is:** what one row represents.

That's the whole definition, and it's the single most common source of silently
wrong numbers in analyst work.

**The example.** Two tables:

```
orders        one row = one order                    (1,000 rows)
order_items   one row = one product line in an order (3,400 rows)
```

Join them and SQL copies each order row once per line item. Sum the order total
and you get 3.4× the real revenue. No error. The join was valid.

**In this project:** one row is one *permit revision*, not one permit. 438,949
rows, 393,521 permits. Counting rows overstates by 11.5%.

**The habit:** before any `SUM`, `AVG` or `COUNT`, ask *what does one row
represent now* — after the joins, not before.

> **Test yourself.** A query joins customers → orders → order_items, filters to
> June, and returns `COUNT(customer_id) = 3,400`. The company has 500 customers.
> What went wrong, and what are the two fixes?

---

## Fan-out

**What it is:** when a join duplicates rows and inflates your totals.

It's the mechanism behind the grain problem. One row on the left matching three
on the right produces three rows, each carrying a copy of the left-hand values.

**The tell:** your result set has more rows than the table you started from.

---

## Right-censoring

**What it is:** the slow cases haven't finished yet, so they're missing from
your data entirely.

**The everyday version:** judging a marathon by who's crossed the line an hour
in. Everyone you can see is fast. That's not the race, that's the clock.

**In this project:** the file contains only *closed* permits. A 2026 permit
appears only if it was approved and closed fast. So 2026 looks brilliant —
8 days — and the number is meaningless.

**The proof:** 100% of 2026 permits closed within a year, versus 52% of 2017's.
Not efficiency. Arithmetic.

> **Test yourself.** A hospital reports that patients admitted this month have
> an average stay of 2 days, down from 6 last year. What's the obvious
> explanation before you celebrate?

---

## Survivorship bias

Right-censoring's bigger family. What you can see is a *survivor* sample, not
the population — and the survivors are systematically different.

**The classic:** WWII engineers examined returning bombers to decide where to
add armour. The right answer was to armour where the returning planes *weren't*
hit — because planes hit there didn't return.

---

# STAGE 2 — EXCEL AND POWER QUERY

## Applied Steps are ordered

Power Query records each transformation and replays them top to bottom, every
refresh. The order isn't history — it's logic.

**In this project, the order of two steps is worth more than everything else in
the workbook.** Cost values are written `50,000`, with a comma. Convert the
column to a number *before* stripping the commas and Excel turns 52,000 real
values into blanks. No error, no warning. A quarter of the usable cost data.

Strip first, convert second: 146,490 usable values becomes 198,439.

> **Test yourself.** Why doesn't Power Query raise an error when a value fails
> to convert? What does it do instead, and why is that worse?

---

## Live formulas, not pasted values

A cell containing `=AVERAGEIFS(...)` recalculates when its inputs change. A cell
containing `55.0158` doesn't.

A workbook of pasted numbers is a screenshot. A workbook of formulas is a
model. In an interview, "every derived value is a live formula" is a specific,
checkable claim.

**In this project:** 107,380 formulas, zero errors.

---

## INDEX/MATCH

Excel's lookup workhorse, and worth knowing over `XLOOKUP` because it works
everywhere including older files and LibreOffice.

- `MATCH(value, range, 0)` → which *position* holds this value
- `INDEX(range, position)` → give me what's at that position

Together: find where, then fetch what.

**In this project:** assigning each permit a cost band by matching its cost
against a band table, with match type `1` (largest value ≤ lookup).

---

## Flag, don't delete

When you find a bad row, mark it. Don't remove it.

A deleted row can't be audited. Nobody can check what was dropped or why, and
the row count silently stops matching the source.

**In this project:** every one of the 438,949 rows survives into the database,
carrying flags — `flag_never_issued`, `flag_future_date`, `is_review_analysable`.
The filtering happens in SQL views, where it's visible in one file and
reversible by editing a `WHERE` clause.

---

# STAGE 3 — SQL

## Star schema

**What it is:** one big table of *events* (the fact table), surrounded by small
lookup tables of *descriptions* (dimensions).

```
              dim_date
                  │
dim_geography ── fact_permits ── dim_permit_type
                  │
             dim_status
```

**Why not one wide flat table?** Three reasons: every description would repeat
on every row; renaming a permit type would be a mass update instead of a
one-cell edit; and there'd be nowhere clean to put an Unknown member.

---

## Primary key, composite key

A **primary key** uniquely identifies a row. A **composite key** is when it
takes two or more columns together to be unique.

**In this project, both obvious candidates failed.** `PERMIT_NUM` isn't unique
— permits have revisions. And `PERMIT_NUM + REVISION_NUM` isn't unique either,
because Toronto issues *conditional permits* that share a number with the full
permit that follows.

The real key needs a third column: permit + revision + type.

**The trap inside the trap:** those conditional permits get marked `Cancelled`
when the real permit arrives. They look like failed projects. They're
successful conversions. Counting them as failures inflates the cancellation
rate.

> **Test yourself.** You're told to deduplicate a table on its "obvious" key and
> 3,491 groups collide. Before you write `DROP DUPLICATES`, what's the one thing
> you must check?

---

## Unknown member

When a fact row has no matching dimension row, its foreign key is NULL — and
every `INNER JOIN` silently drops it. No error. Just a total that's quietly
short.

**The fix:** an explicit "Unknown" row in the dimension (key 0), and unmatched
facts point at it. The rows still join, and their unknown-ness becomes visible
instead of invisible.

**In this project:** five permits had no ward code. The automated QA agent
caught them; manual review had missed them three times.

---

## Filter in views, not in the table

The fact table holds everything. The views hold the exclusions.

That way every exclusion lives in one file a reviewer can read, and relaxing
one is a text edit rather than a reload.

---

# STAGE 4 — PYTHON AND STATISTICS

## Median vs mean

The **mean** adds everything and divides. The **median** is the middle value.

When a distribution has a long tail, the mean gets dragged toward the extremes
and describes nobody.

**In this project:** median 22 days, mean 55. The p90 is roughly four times the
median. Most people wait about three weeks; a few wait years. *55 days* is
nobody's experience.

**When to use which:** median for "what's typical". Mean when you need totals
to add up (revenue per customer × customers = total revenue).

---

## Why Mann-Whitney, not a t-test

A **t-test** compares averages and assumes roughly normal data — the bell
curve.

This data isn't remotely normal: most permits clear in under a month, a few
take years. Heavily right-skewed.

**Mann-Whitney U** compares *ranks* instead of averages, so the shape doesn't
break it.

**The one-liner:** pick the test that matches the shape of your data, not the
one you remember.

---

## p-value vs effect size — the trap

A **p-value** answers: could this difference be chance?
An **effect size** answers: is the difference big enough to care about?

**They are not the same question, and with enough data they diverge completely.**

**In this project:** the district comparison returned
**p = 0.000000000000002** — "highly significant."

The actual difference was **zero days**.

With n = 26,568, a test detects differences far too small to matter. Reporting
that p-value alone would have been technically true and completely misleading.

**The habit:** never quote a p-value without an effect size beside it.

> **Test yourself.** A study of 2 million users finds a new button colour
> increases clicks with p < 0.001. The lift is 0.02%. Should the company ship it?

---

## Hold a variable constant

When group A looks worse than group B, ask whether they're doing the *same
thing* before concluding one is worse at it.

**In this project:** East Toronto looked 65% slower than South. But they handle
different permit mixes. Comparing the same permit type:

- Simple residential: South 15 days, East 15 days — **no gap at all**
- New houses: South 30, East 47.5 — a real gap

**The conclusion changed** from "East is slow" to "complex permits diverge by
district, simple ones don't." The second is more precise and more useful —
it tells a manager *what* to fix.

---

## MNAR — missing not at random

Three kinds of missing data:

| Type | Meaning | Safe to drop? |
|---|---|---|
| MCAR | Missing completely at random | Usually |
| MAR | Missing depending on other columns | With care |
| **MNAR** | **Missing *because of* what the value would be** | **No — it biases everything** |

**In this project:** the cost field is blank on 95% of mechanical permits and
0% of new-house permits. Not random — plumbing permits don't *have* a
construction cost.

So averaging cost across all permit types compares a group that reports cost
against one that structurally can't, and the answer looks perfectly sensible.

> **Test yourself.** A satisfaction survey goes only to customers whose order
> arrived on time. 40% of orders have no score. Your manager says drop the
> blanks and average the rest. Which way is the number wrong, and why?

---

# STAGE 5 — DASHBOARDS

## One axis, never two

A dual-axis chart puts two different measures on two different scales in one
plot. The alignment between those scales is **arbitrary** — so the chart
invents a relationship the data doesn't contain.

**Instead:** two charts, small multiples, or index both series to a common
base so they share one scale.

---

## Ordinal vs categorical colour

- **Categorical** — unordered things (products, teams). Distinct hues.
- **Ordinal** — ordered things (cost bands, complexity tiers). *One* hue, light
  to dark.

Using distinct hues on ordered categories throws away information the reader
needs. Using a ramp on unordered ones implies an order that doesn't exist.

---

## Validate colour, don't eyeball it

Roughly 1 in 12 men has some form of colour-blindness. "These look different
enough" is not a test.

**In this project:** the first palette used grey for the "misleading" line —
it felt right, muted and deprecated. The validator rejected it: grey fails the
chroma floor and can't serve as one of two series people must tell apart.
Orange passed.

**A tool caught a taste decision that would have quietly failed some readers.**

---

## Every visual answers a question

A chart with no question behind it is decoration.

Standard hierarchy: **KPI row** (where are we) → **trend** (which way are we
going) → **diagnostic** (where is it concentrated) → **detail** (which exact
row needs attention).

---

# STAGE 6 — AI AND AUTOMATION

## AI phrases, never computes

The dangerous design is: hand the question and the data to a model, let it
answer. It will produce numbers, in fluent confident prose, and some of them
will be invented.

**The safe design:** the database computes; the model phrases what it's handed.

In this project the model never sees the data. A question routes to one of six
reviewed SQL queries, PostgreSQL computes, and the model receives finished
numbers. Every answer prints its SQL.

---

## Checks must be deterministic

A data-quality check has to give the same answer every day. Ask a model "does
this look right" and it won't.

AI's real contribution was *writing* the checks — turning a human's list of
"things that must stay true" into executable assertions. The verdicts are
arithmetic.

**An AI that grades its own homework is not a safety net.**

---

## Automate only what's validated

Do it by hand. Check it. *Then* write the program.

Automating first would have encoded the two errors the manual work caught.
**Automation multiplies whatever it's given, mistakes included.**

---

## Approval gates

An automated pipeline that can publish to a stakeholder is a liability with a
schedule attached.

This one prepares, checks, and stops. A person reads the QA output and decides.

---

# THE ONE IDEA BEHIND ALL OF IT

Every defect in this project produced **no error message**.

Wrong grain, a placeholder in a currency column, comma-formatted numbers, a
misread date field, a NULL key, a significant p-value on a zero difference —
all of them return something that looks exactly like an answer.

Tools catch broken syntax. They don't catch wrong thinking.

**That gap is the job.**
