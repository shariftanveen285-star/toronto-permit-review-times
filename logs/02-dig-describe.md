# Log 02 — DIG Stage D: DESCRIBE

**Dataset:** Toronto Cleared Building Permits since 2017
**Source:** City of Toronto Open Data, CKAN resource `a96c0ba4-3026-402b-b09d-5b1268b8f810`
**File:** `data/raw/cleared_permits_since_2017.csv` · 142 MB · md5 `d5f431c2522692932fbb6040c39ccf54`
**Captured:** 2026-09-20 · portal `metadata_modified` 2026-09-20T11:17:04
**Script:** `python/01_profile.py`

**Rule in force:** nothing is fixed, filled or dropped at this stage. Find out
what it *means* first. (Charter, DIG-D step 6.)

---

## Shape

| | |
|---|---|
| Rows | 438,949 |
| Columns | 32 |
| `APPLICATION_DATE` range | 1979-06-21 → 2026-09-17 |
| `ISSUED_DATE` range | 1979-11-27 → 2026-09-17 |
| `COMPLETED_DATE` range | 2017-01-01 → 2028-11-03 |

---

## FINDING 1 — The obvious primary key does not hold

**Classification: Verified fact.**

`PERMIT_NUM` alone is not unique (393,521 distinct across 438,949 rows — a
1.116 fan-out). That much was expected: permits have revisions.

But `(PERMIT_NUM, REVISION_NUM)` **is also not unique.** 3,491 key groups,
6,982 rows.

Critically: **zero** of those 3,491 groups are exact duplicates. Every one
genuinely differs — and they differ across nearly every column, including
`PERMIT_TYPE`, `STATUS` and all three dates.

Sample:

| PERMIT_NUM | REV | PERMIT_TYPE | STATUS | APPLIED | ISSUED | COMPLETED |
|---|---|---|---|---|---|---|
| 04 139182 BLD | 00 | Conditional Permit | **Cancelled** | 2004-08-27 | *(null)* | 2025-06-25 |
| 04 139182 BLD | 00 | New Houses | **Closed** | 2004-05-26 | 2004-11-10 | 2026-01-29 |

**Interpretation (INFERENCE, not yet confirmed against City documentation):**
a Conditional Permit is a distinct permit record that shares a permit number
with the full permit it precedes. Toronto issues conditional permits to let
work begin before full approval; the conditional record is later cancelled
when the full permit is issued.

**Why this matters, two ways:**

1. **Deduplicating naively destroys real records.** A `DROP DUPLICATES` on the
   composite key would delete one half of a genuine permit pair.
2. **Ignoring it corrupts the cancellation rate.** Those `Cancelled`
   conditional records are not failed projects — they are *successful*
   conversions to a full permit. Counting them as cancellations overstates
   project failure.

**Decision:** true grain is `(PERMIT_NUM, REVISION_NUM, PERMIT_TYPE)`. To be
verified against City of Toronto permit documentation before the schema is
built.

### Fan-out, quantified

| Measure | Value |
|---|---|
| `COUNT(*)` — the naive "permits" figure | 438,949 |
| `COUNT(DISTINCT PERMIT_NUM)` — actual permits | 393,521 |
| **Overstatement** | **45,428 (11.5%)** |

Any report that counts rows and calls them permits is 11.5% wrong before it
starts.

---

## FINDING 2 — `COMPLETED_DATE` does not mean construction was completed

**Classification: Verified fact (the evidence) + Hypothesis (the mechanism).**

This is the most consequential finding in the profile, and it is invisible
unless you look.

The evidence:

- `APPLICATION_DATE` reaches back to **1979**. 36,480 permits in this file
  were applied for **before 2010**.
- `COMPLETED_DATE` begins at **exactly 2017-01-01** — the dataset's own
  inclusion boundary, not a natural start.
- Raw `ISSUED → COMPLETED` interval: median **514 days**, p95 **6,860 days
  (18.8 years)**, max **17,097 days (46.8 years)**.

Construction does not take 46 years. `COMPLETED_DATE` is the date the City
**administratively cleared the file** — closed the record — not the date the
building was finished. The dataset is named "Cleared Permits" and it means it.

**Consequence:** `COMPLETED_DATE − ISSUED_DATE` is *not* a construction
duration. It is a records-management latency. Treating it as build time — the
obvious reading, and the one most analyses of this data would take — produces
a number that is confidently and completely wrong.

**Related observation — a records purge:** completions per year run
~33,000–41,000 from 2017 through 2024, then jump to **62,289 in 2025** and
**69,647 in 2026**. That is not a construction boom; it has the shape of a
backlog clean-up. Any year-over-year trend spanning 2024→2025 is measuring
City administrative behaviour, not building activity.

**Consequence for the project:** `APPLICATION → ISSUED` (the City's review
queue) is the defensible cycle-time metric. `ISSUED → COMPLETED` is not, and
will be explicitly excluded with this reasoning stated.

---

## FINDING 3 — Half of the cost field is a literal instruction string

**Classification: Verified fact.**

`EST_CONST_COST` is typed `text`. 274,683 of 421,173 non-null values (65%)
fail a numeric cast. Two distinct causes:

**(a) A sentinel string — 222,734 rows (50.7% of the entire dataset):**

```
DO NOT UPDATE OR DELETE THIS INFO FIELD
```

A system placeholder, sitting in a currency column, in published open data.

**(b) Comma-formatted numbers — 51,949 rows:** `"50,000"`, `"100,000"`.

Stripping commas recovers parseable values from 146,490 → **198,439**. A naive
`pd.to_numeric(errors="coerce")` silently discards **51,949 real cost values** —
about a quarter of the usable data — with no error and no warning.

### The sentinel is not random — it is structural

| PERMIT_TYPE | n | sentinel rate |
|---|---|---|
| Mechanical (MS) | 81,745 | **95.3%** |
| Drain and Site Service | 52,060 | **94.5%** |
| Designated Structures | 11,968 | **93.5%** |
| Plumbing (PS) | 94,115 | **86.8%** |
| Building Additions/Alterations | 48,009 | 1.6% |
| Small Residential Projects | 89,312 | 1.0% |
| New Houses | 23,901 | **0.0%** |
| Demolition Folder (DM) | 12,612 | **0.0%** |

The split is clean: **trade permits** (plumbing, mechanical, drain) do not
carry a construction cost; **building permits** do.

This is **missing not at random (MNAR)**. Any cost-based metric is valid only
within the building-permit families. Averaging cost across all permit types
would silently compare a population that reports cost against one that
structurally cannot — and the result would look perfectly reasonable.

**Also present:** 44,161 values are zero or negative; maximum is
$1,000,000,000 (a suspiciously round figure worth inspecting).

---

## FINDING 4 — `WARD_GRID` is a compound field

**Classification: Verified fact + Hypothesis on the encoding.**

463 distinct values, uniformly 5 characters, zero nulls. First character:

| Prefix | Rows |
|---|---|
| S | 202,465 |
| N | 107,422 |
| W | 73,202 |
| E | 55,852 |
| **C** | **3** |

Pattern `[LETTER][2 digits][2 digits]` — e.g. `N0823`, `E2530`, `S1228`.

**Hypothesis:** the letter is a former-municipality district (S/N/W/E), and the
digits encode ward and map-grid square. To be confirmed against City
documentation, not assumed.

**`C` with 3 rows out of 438,949 is almost certainly a data-entry error** and
needs individual inspection rather than a rule.

Toronto has 25 wards, so `WARD_GRID` must be **parsed**, not used as a
dimension key directly. A `dim_geography` table is required.

---

## FINDING 5 — Other quality issues catalogued, not yet resolved

| Issue | Magnitude | Note |
|---|---|---|
| `BUILDER_NAME` null | **95.1%** | The "supplier" dimension is effectively unusable. Scope decision required. |
| `DWELLING_UNITS_CREATED` null | 64.5% | Also: minimum is **−13**. Negative units created is impossible; needs a meaning, not a clamp. |
| `DWELLING_UNITS_LOST` null | 64.9% | |
| `ISSUED_DATE` null | 7.9% (34,702) | Correlates with `Cancelled` / `Refused` — permits that never issued. Legitimate, not missing. |
| `ISSUED` before `APPLICATION` | 21 rows | Impossible sequence. Min interval −284 days. |
| `COMPLETED` before `ISSUED` | 3 rows | |
| `COMPLETED` in the future | 3 rows | Max 2028-11-03. |
| `CURRENT_USE` / `PROPOSED_USE` | 11,155 / 15,292 distinct | Free-text. Unusable as dimensions without standardisation. |

### `STATUS` distribution

| Status | Rows |
|---|---|
| Closed | 379,174 |
| Cancelled | 42,641 |
| Closed - Dormant | 14,550 |
| Approved | 1,795 |
| Superseded | 591 |
| *(10 more, each < 100)* | |

**Cancelled (9.7%) and Closed-Dormant (3.3%) must be excluded from cycle-time
analysis** — a permit that never issued has no review duration. Including them
would pull the median toward zero via nulls, or toward infinity via
administrative closure dates, depending on the join.

---

## What Describe changed about the plan

1. **Cycle time = `APPLICATION → ISSUED` only.** Finding 2 disqualifies the
   completion interval. Stated, not hidden.
2. **Cost analysis scoped to building-permit families.** Finding 3 makes any
   cross-type cost average meaningless.
3. **Grain is a 3-part key**, pending confirmation. Finding 1.
4. **`dim_geography` must parse `WARD_GRID`.** Finding 4.
5. **`BUILDER_NAME` is out of scope** at 95.1% null — unless a sub-population
   with reliable coverage can be identified.
6. **No trend may span 2024→2025** without noting the records purge.

---

## Open questions for Introspect (DIG-I)

- Is review time (`APPLICATION → ISSUED`) getting better or worse by year?
- Does it differ by district, and is the difference statistically real or
  noise?
- Does permit complexity (type, cost band, dwelling units) explain review
  time — or does the district matter more than the work?
- Is the conditional-permit route actually faster to a shovel in the ground?
  That is a genuine decision-relevant question a City stakeholder would care
  about.
- **Untestable with this data:** anything about *why* a permit was slow. There
  is no reviewer, no department, no hold-reason field. This must be stated
  rather than inferred.
