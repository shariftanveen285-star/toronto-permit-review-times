# Log 03 — DIG Stage I: INTROSPECT (and hypothesis testing)

**Question:** How long does Toronto take to approve a building permit, is it
getting better or worse, and does it depend on where you build or what you
build?

**Metric:** `APPLICATION_DATE → ISSUED_DATE`, in days. Median, not mean — the
distribution has a long right tail, so a mean describes nobody's actual wait.

**Excluded:** `ISSUED → COMPLETED`. Finding 2 of Log 02 showed it is a records-
closure latency, not construction time.

---

## FINDING A — The headline trend is an artifact. The real trend is the opposite.

**Classification: Verified fact.**

### What the raw data appears to say

| Application year | Median days to approve |
|---|---|
| 2017 | 26 |
| 2020 | 29 |
| 2023 | 30 |
| 2024 | 24 |
| 2025 | 19 |
| 2026 | **8** |

Read naively: *Toronto's permit review has become 69% faster since 2017.* This
is the chart that would have gone in the dashboard.

It is wrong.

### Why it is wrong — right-censoring

This file contains only permits the City has already **administratively
closed**. A permit applied for recently can only appear in it if it was
approved *and* closed quickly. Slow recent permits are not in the file yet —
they are still open.

So recent years contain a survivor sample of fast permits, by construction.

**Proof 1 — each cohort's closing speed:**

| Application year | % closed within 1 year of issue |
|---|---|
| 2017 | 51.6% |
| 2021 | 44.8% |
| 2024 | 69.5% |
| 2025 | 90.6% |
| 2026 | **100.0%** |

Every single 2026 record closed within a year. Not because 2026 was efficient
— because nothing else *could* be in the file.

**Proof 2 — the mechanical ceiling.** The longest review time observable for a
cohort is bounded by the calendar, and the data sits right against that bound:

| Application year | Longest review observed | Days of window available |
|---|---|---|
| 2020 | 2,224 | 2,265 |
| 2023 | 1,251 | 1,177 |
| 2025 | 573 | 461 |
| 2026 | **208** | **168** |

The observed maximum is not measuring City performance. It is measuring how
long ago the year was.

### The fair comparison

Restrict **every** year to permits closed within 365 days of issue. Same rule
for all cohorts, so the comparison is like for like.

| Application year | Median days (fair) | p90 (fair) |
|---|---|---|
| 2017 | 20 | 91 |
| 2018 | 19 | 68 |
| 2019 | 21 | 80 |
| 2020 | 22 | 93 |
| 2021 | 24 | 111 |
| **2022** | **29** | **116** |
| 2023 | 27 | 114 |
| 2024 | 20 | 93 |
| 2025 | 18 | 70 |

n = 145,326 records.

**The real story: review times got 45% WORSE between 2017 and 2022, then fully
recovered.**

### Statistical tests

| Hypothesis | Test | Result |
|---|---|---|
| 2022 slower than 2017 | Mann-Whitney U | **p = 3.6 × 10⁻¹⁴⁰** · +9 days (+45%) · rank-biserial +0.160 |
| 2025 faster than 2022 | Mann-Whitney U | **p = 7.1 × 10⁻¹⁴⁸** |
| 2025 differs from 2017 | Mann-Whitney U (two-sided) | **p = 0.807 — no significant difference** |

Mann-Whitney rather than a t-test because the distribution is heavily skewed,
not normal.

**Interpretation:** the deterioration is real and large. The recovery is real
and complete — 2025 is statistically indistinguishable from 2017.

**Association, not causation.** The 2021–22 peak coincides with pandemic
disruption and a construction surge. This dataset contains no staffing,
workload or department fields, so **the cause cannot be tested here.** It is
named as a hypothesis, not a conclusion.

**Excluded from all trend reporting: 2026.** Only 4,046 records, 100%
fast-closers, mechanical ceiling of 208 days. Not a year, a sliver.

---

## FINDING B — The district gap is mostly composition, not performance

**Classification: Verified fact.**

### What the raw data appears to say

| District | Median days | p90 |
|---|---|---|
| East | 38 | 353 |
| West | 34 | 239 |
| North | 31 | 235 |
| South | 23 | 109 |

Read naively: *East Toronto is 65% slower than South.* A tempting headline.

### Holding permit type constant

| Permit type | South | East | Gap | p | Effect size |
|---|---|---|---|---|---|
| Small Residential Projects | 15 | 15 | **0 days** | 1.8×10⁻³ | **+0.031 (negligible)** |
| Building Additions/Alterations | 28 | 35 | +7 days | 2.9×10⁻⁷⁰ | +0.248 (medium) |
| New Houses | 30 | 48 | **+17 days** | 5.1×10⁻⁶ | +0.183 (small–medium) |

**Between South and East, simple permits show no gap at all.** Identical
medians, and an effect size of 0.031 — statistically detectable only because
n = 17,413, and practically meaningless.

**Correction, and it matters.** Extending the simple-permit comparison to all
four districts does *not* give a flat result. The medians are South 15, North
15, East 15 — and **West 20**. Three of four are identical; West is genuinely
slower even on simple work.

An earlier draft of this log claimed "no district gap at all" for simple
permits. That was wrong: it generalised a two-district test to four. The claim
is corrected here rather than quietly amended, because the error is instructive
— it is exactly the over-generalisation this framework exists to catch, and it
survived one pass of my own review.

The complexity pattern still holds: the gap widens with project complexity in
every district. West is simply slower across the board rather than only on
complex work.

**Note on p-values vs effect sizes.** Kruskal-Wallis across all four districts
on Small Residential returns p = 2.1 × 10⁻¹⁵ — "highly significant." The effect
size says the difference is trivial. At n = 26,568, significance testing detects
differences too small to matter. **Reporting that p-value without the effect
size would have been technically true and practically misleading.**

**Revised conclusion:** not "East is slow." Rather — *simple permits move at
the same speed everywhere in Toronto; complex permits diverge by district, and
the gap widens with project complexity.* That is a more precise claim and a
more useful one.

---

## FINDING C — Project cost predicts review time, monotonically

**Classification: Association.** Guarded to building permits only, per
Finding 3 of Log 02 (cost is MNAR by permit type).

n = 38,676. Spearman ρ = **+0.192**, p ≈ 0.

| Cost band | n | Median days | p90 days |
|---|---|---|---|
| under $25k | 13,748 | 17 | 90 |
| $25k–100k | 13,698 | 21 | 85 |
| $100k–500k | 8,754 | 29 | 91 |
| $500k–5M | 2,324 | 34 | 98 |
| over $5M | 152 | **54** | **1,086** |

Perfectly monotonic — every step up in cost adds review time.

**The striking number is the p90 for projects over $5M: 1,086 days.** The
slowest 10% of large projects wait roughly three years. Median for that band is
54 days, so the distribution is extraordinarily wide — most large projects move
reasonably; a minority stall for years.

ρ = 0.192 is a weak correlation. Cost is a real but partial signal — it
explains some of the variation in review time, not most of it. Stated plainly
rather than dressed up.

---

## What cannot be answered with this data (Untestable)

Named explicitly, because claiming otherwise would be the failure mode this
whole framework exists to prevent:

- **Why** any permit was slow. No reviewer, department, hold-reason, or
  resubmission-count field exists.
- Whether the 2021–22 deterioration was caused by staffing, pandemic policy, or
  application volume. No workload data.
- Whether applicant quality matters — no resubmission or deficiency data.
- Anything about permits still open. This file contains closed permits only,
  which is the root of Finding A.

---

## Carried into Goal-setting (DIG-G)

**Audience:** City operations / building division management.

**Business problem:** review times deteriorated 45% then recovered — but the
recovery is uneven, and complex permits in outer districts still lag.

**Decision the analysis supports:** where to direct reviewer capacity —
specifically, whether complex-permit review in East and West warrants
dedicated resourcing.

**KPIs:** median days to issue · p90 days to issue · % issued within 30 days ·
all reported on the fair-window basis with the censoring caveat attached.

**Deliverable:** dashboard with the censoring correction built in, so the
default view cannot show the false "improving" trend.
