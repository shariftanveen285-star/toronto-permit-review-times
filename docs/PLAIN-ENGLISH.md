# This Project, In Plain English

A running translation of everything we build. No jargon. If a technical word
has to appear, it gets explained right there in normal words.

This is the doc to read before an interview.

---

## What the project is, in three sentences

The City of Toronto publishes a file of every building permit it has closed
since 2017. A building permit is permission to build something. We are
analysing how long the City takes to say yes, whether it is getting faster or
slower, and whether some parts of the city are slower than others.

---

## Why anyone would care

If you want to build a house, an extension, or a shop in Toronto, you apply
for a permit and then you wait. While you wait, you are paying for land,
loans, and sometimes a crew standing around.

So "how long is the wait, and is it getting worse?" is a real question with
real money attached. That makes it a fair thing to analyse.

---

## What we found before doing any analysis

We looked at the data first, before calculating anything. That is the whole
point of the "Describe" step. Four things turned up. Each one would have
ruined the analysis if we had missed it.

---

### 1. The same permit can appear twice

You would expect one row in the file to mean one permit. It doesn't.

Two reasons:

**Reason one — revisions.** If someone changes their plans, the permit gets a
revision. Each revision is its own row. So one permit can be three or four
rows.

**Reason two — conditional permits.** Toronto sometimes gives you a temporary
"you can start digging" permit while the full permit is still being processed.
Both permits share the same permit number. So they land in the file as two
rows that look like duplicates but aren't.

**Why it matters:** if you count the rows and call that "permits", you are
over by 11.5%. That is 45,428 permits that don't exist.

**The trap inside the trap:** those temporary permits get marked
**"Cancelled"** once the real permit comes through. They look like failed
projects. They are actually the opposite — they are projects that succeeded
and moved on. Count them as failures and your cancellation rate is wrong.

---

### 2. The "completed" date does not mean the building was finished

This is the big one.

The file has a column called `COMPLETED_DATE`. The obvious reading is "the
date the building work finished."

We checked. Some permits show a gap of **46 years** between being issued and
being "completed."

Nobody takes 46 years to build a house.

**What it actually means:** it's the date a City clerk closed the paperwork.
Not the date anything got built. Some of these are old files from the 1980s
that somebody finally tidied up in 2019.

**Why it matters:** if you use this column to measure "how long construction
takes", you get a number that is completely wrong — but looks fine. Nothing
errors. You just quietly publish nonsense.

**What we do instead:** we only measure from *applied* to *approved*. That
part is real, and it's the part the City actually controls.

**One more thing we spotted.** The number of permits "completed" each year
sits around 35,000–40,000 from 2017 to 2024. Then it jumps to 62,000 in 2025
and 70,000 in 2026.

That is not a building boom. That is the City clearing out a backlog of old
paperwork. So if we showed a chart of "completions per year", it would look
like Toronto exploded with construction. It didn't. The filing cabinet just
got cleaned.

---

### 3. Half the cost column is a note to staff

There is a column for estimated construction cost. Half of it — 222,734 rows —
contains this text:

> DO NOT UPDATE OR DELETE THIS INFO FIELD

That is a message from one City employee to another, sitting in a column that
is supposed to contain dollar amounts. It got published by accident.

**And it's not random.** We checked which permits have it:

- Plumbing permits: 87% have the placeholder
- Heating and cooling permits: 95%
- New house permits: 0%

So it's not "some data is missing." It's **plumbing permits don't have a
construction cost, because that isn't a thing for plumbing permits.**

**Why it matters:** if you take an average cost across all permits, you're
mixing a group that reports cost with a group that never could. The answer
comes out looking perfectly sensible and is meaningless.

**The other cost problem.** About 52,000 rows write the number with a comma,
like `50,000`. Standard tools read that as text, not a number, and throw it
away silently. That's a quarter of the usable cost data gone without a
warning. We had to strip the commas first.

---

### 4. The location column is three things stuck together

There's a column called `WARD_GRID` with values like `N0823`.

Toronto has 25 wards. This column has 463 different values. So it isn't a ward.

It's a letter (which part of the old city — North, South, East, West) plus two
numbers (the ward, and a map square). Three pieces of information jammed into
one column.

We have to split it apart before we can group anything by area.

**Small thing worth mentioning:** three rows out of 438,949 start with `C`,
which doesn't match anything. Almost certainly a typo. We look at those three
by hand rather than writing a rule for them.

---

## The one habit behind all four

Before calculating anything, ask: **what does one row actually mean?**

Every one of these problems came from that question. None of them would have
produced an error message. All four would have produced confident, wrong
numbers.

---

## Words you'll hear, in normal English

| Word | What it actually means |
|---|---|
| **Grain** | What one row represents. "One row = one permit revision." |
| **Fan-out** | When joining tables accidentally copies rows and inflates your totals |
| **Primary key** | The column (or columns) that uniquely identify a row |
| **Composite key** | When it takes two or more columns together to be unique |
| **MNAR** | Data is missing *because of what the answer would have been*. The dangerous kind |
| **Sentinel value** | A fake value used as a placeholder. Like `DO NOT UPDATE` in a cost field |
| **Star schema** | A big table of events, surrounded by small lookup tables for things like dates and places |
| **Cycle time** | How long something takes from start to finish |

---

# Part Two — what we built, and what it found

## The answer to the question

**How long does Toronto take to approve a permit?**

About **three weeks** (22 days) is typical.

**Is it getting better or worse?** This is where it gets interesting.

The raw numbers say approvals got much faster — 26 days in 2017 down to 8 days
in 2026. That is false, for the reason in Part One: the file only contains
permits that have already been closed, so recent years only show the fast ones.

Comparing every year by the same rule:

| Year | Days to approve |
|---|---|
| 2017 | 20 |
| 2020 | 22 |
| **2022** | **29 — the worst** |
| 2024 | 20 |
| 2025 | 18 |

So approvals got **45% slower** between 2017 and 2022, then recovered
completely.

I checked whether that could be chance. It can't — the odds against are
astronomical. And 2025 versus 2017 came back as *no meaningful difference*,
which means the recovery is finished, not partial.

**What I can't tell you is why.** The data has no column for staffing, workload,
or reasons for delay. The timing lines up with the pandemic, but I'd be
guessing, so the write-up says so plainly.

## Does it matter where you build?

Raw numbers said East Toronto takes 38 days and South takes 23 — so East looks
65% slower.

But those areas handle different *kinds* of permits. Comparing like with like:

| Type of permit | South | North | East | West |
|---|---|---|---|---|
| Small residential | 15 | 15 | 15 | 20 |
| Additions / alterations | 28 | 31 | 35 | 34 |
| New houses | 30 | 35 | 48 | 50 |

Three of the four areas handle simple permits at exactly the same speed. The
gap only appears on complicated work, and grows as the work gets more complex.

That's far more useful to a manager than "East is slow" — it says *what* to fix.

## Does the size of the project matter?

Yes, steadily:

| Project cost | Typical wait |
|---|---|
| under $25k | 17 days |
| $100k–500k | 28 days |
| over $5M | 51 days |

But the slowest 10% of projects over $5M wait **1,036 days** — nearly three
years. Most big projects move fine. A few get stuck badly.

---

# What each piece of software did

## Excel

Cleaned the data and built a workbook where every number is a **live formula**,
not a typed-in result. Change a cell and everything recalculates.

107,380 formulas. Zero errors.

Used `INDEX/MATCH` to look values up, and `COUNTIFS` / `AVERAGEIFS` to count
and average with conditions.

## Power Query

The part of Excel that records your cleaning steps and replays them
automatically next time. I wrote out every step and the code behind it, so
somebody else could reproduce it exactly.

## PostgreSQL (the database)

Reorganised 438,949 rows into five connected tables — one big table of permits
plus four small lookup tables for dates, places, permit types and statuses.

That shape is called a **star schema**, and it's how nearly every reporting
database is built.

## Python

Did the statistical testing. Not "this chart looks like a trend" but an actual
test of whether the difference could be chance.

Also built the automation and the quality checker.

## The dashboard

An interactive web page anyone can open. It deliberately opens with a warning
explaining why the obvious trend is wrong — before showing any chart.

## The AI layer

Three pieces:

1. **Ask the data** — type a question in plain English, get an answer. Built so
   the AI *cannot* make up numbers: the database calculates, the AI only writes
   the sentence, and every answer shows the query behind it.
2. **Quality checker** — 16 automatic checks. Found a real bug I'd missed.
3. **Pipeline** — runs the whole thing on new data, with safety gates, and
   stops before publishing anything so a person decides.

---

# Three things to say if asked

**"What was hard?"**
Realising the improving trend was fake. That chart looked completely
believable. What gave it away was the record count falling every year — if
applications were steady, that shouldn't happen.

**"How do you know you're right?"**
Every headline number was calculated three separate ways — Excel, the database,
and Python — and all three agree to four decimal places. There's a tab in the
workbook showing them side by side.

**"Did the AI actually do anything?"**
It found a bug three rounds of manual review had missed — five rows being
silently dropped from every query. No effect on any published number, but I
fixed the structure anyway, because next month those rows might not be harmless.
