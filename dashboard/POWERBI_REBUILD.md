# Power BI Rebuild Guide

Exact specification to reproduce the published dashboard as a native `.pbix`.

**Why this file exists, stated plainly:** Power BI Desktop was not available in
the build environment, so the dashboard was built as an interactive web page
instead. Rather than imply a `.pbix` exists, this guide makes the web version
and a native version provably equivalent — same model, same measures, same
visual-to-field mapping. Anyone with Power BI Desktop can rebuild it in an hour
and get identical numbers.

---

## 1. Data model

Import the five files from `data/processed/`. Star schema, single-direction
filters from dimensions to the fact.

| Table | Type | Key | Rows |
|---|---|---|---|
| `fact_permits` | Fact | `permit_sk` | 438,949 |
| `dim_date` | Dimension | `date_key` | 18,034 |
| `dim_geography` | Dimension | `geography_key` | 463 |
| `dim_permit_type` | Dimension | `permit_type_key` | 23 |
| `dim_status` | Dimension | `status_key` | 21 |

### Relationships

| From | To | Cardinality | Direction | Active |
|---|---|---|---|---|
| `fact_permits[application_date_key]` | `dim_date[date_key]` | Many-to-one | Single | **Yes** |
| `fact_permits[issued_date_key]` | `dim_date[date_key]` | Many-to-one | Single | No (inactive) |
| `fact_permits[completed_date_key]` | `dim_date[date_key]` | Many-to-one | Single | No (inactive) |
| `fact_permits[geography_key]` | `dim_geography[geography_key]` | Many-to-one | Single | Yes |
| `fact_permits[permit_type_key]` | `dim_permit_type[permit_type_key]` | Many-to-one | Single | Yes |
| `fact_permits[status_key]` | `dim_status[status_key]` | Many-to-one | Single | Yes |

**Role-playing dimension note.** Three date columns point at one `dim_date`.
Power BI allows only one active relationship between two tables, so
`application_date_key` is active and the other two are inactive, reached with
`USERELATIONSHIP` when needed. Do **not** solve this by importing three copies
of `dim_date` — that triples the model and lets two date slicers contradict
each other on the same page.

Mark `dim_date` as a date table on `full_date` (Table tools → Mark as date
table). Time intelligence misbehaves silently without it.

### Model hygiene

- Hide every `*_key` column from report view. They are plumbing.
- Hide `fact_permits[days_to_admin_close]` — see the warning in §2.
- Sort `dim_date[month_name]` by `dim_date[month]`, or months order
  alphabetically.

---

## 2. DAX measures

Create a blank table named `_Measures` and put all of these in it.

### Base filter — the correction, in one measure

Everything else depends on this. It encodes both the analysable-record rule and
the like-for-like closure window.

```dax
Analysable Records =
CALCULATE (
    COUNTROWS ( fact_permits ),
    fact_permits[is_review_analysable] = TRUE (),
    fact_permits[days_to_admin_close] >= 0,
    fact_permits[days_to_admin_close] <= 365
)
```

```dax
Permits =
CALCULATE (
    DISTINCTCOUNT ( fact_permits[permit_num] ),
    fact_permits[is_review_analysable] = TRUE (),
    fact_permits[days_to_admin_close] >= 0,
    fact_permits[days_to_admin_close] <= 365
)
```

> **Use `Permits`, never `Analysable Records`, wherever the label says
> "permits".** A permit with four revisions is four rows. Counting rows
> overstates permits by 11.5% across the full source.

### Headline measures

```dax
Median Days to Issue =
CALCULATE (
    MEDIANX (
        FILTER (
            fact_permits,
            fact_permits[is_review_analysable] = TRUE ()
                && fact_permits[days_to_admin_close] >= 0
                && fact_permits[days_to_admin_close] <= 365
        ),
        fact_permits[days_to_issue]
    )
)
```

```dax
P90 Days to Issue =
CALCULATE (
    PERCENTILEX.INC (
        FILTER (
            fact_permits,
            fact_permits[is_review_analysable] = TRUE ()
                && fact_permits[days_to_admin_close] >= 0
                && fact_permits[days_to_admin_close] <= 365
        ),
        fact_permits[days_to_issue],
        0.90
    )
)
```

```dax
Pct Within 30 Days =
DIVIDE (
    CALCULATE (
        COUNTROWS ( fact_permits ),
        fact_permits[is_review_analysable] = TRUE (),
        fact_permits[days_to_admin_close] >= 0,
        fact_permits[days_to_admin_close] <= 365,
        fact_permits[days_to_issue] <= 30
    ),
    [Analysable Records]
)
```

Format as Percentage, 1 decimal.

> **Median, not average.** The distribution's p90 is roughly four times its
> median. `AVERAGE` would be dragged up by a small number of extreme cases and
> would describe nobody's actual wait. If a stakeholder asks for "the average",
> show both and explain the gap — don't silently swap the measure.

### The uncorrected measure — for the contrast visual only

```dax
Median Days UNCORRECTED =
CALCULATE (
    MEDIANX (
        FILTER ( fact_permits, fact_permits[is_review_analysable] = TRUE () ),
        fact_permits[days_to_issue]
    )
)
```

> **This measure is deliberately biased and exists only to be shown beside the
> corrected one.** Rename it if you like, but keep the word UNCORRECTED in the
> name. A future analyst who finds a bare "Median Days" measure with no closure
> window will use it and publish the wrong trend.

### Censoring-evidence measures

```dax
Pct Closed Within 1 Year =
DIVIDE (
    CALCULATE (
        COUNTROWS ( fact_permits ),
        fact_permits[is_review_analysable] = TRUE (),
        fact_permits[days_to_admin_close] >= 0,
        fact_permits[days_to_admin_close] <= 365
    ),
    CALCULATE (
        COUNTROWS ( fact_permits ),
        fact_permits[is_review_analysable] = TRUE ()
    )
)
```

```dax
Longest Review In File =
CALCULATE (
    MAX ( fact_permits[days_to_issue] ),
    fact_permits[is_review_analysable] = TRUE ()
)
```

### Cost measures — guarded

```dax
Median Est Cost =
CALCULATE (
    MEDIANX (
        FILTER (
            fact_permits,
            fact_permits[cost_is_reported] = TRUE ()
                && fact_permits[est_const_cost] > 0
                && fact_permits[is_review_analysable] = TRUE ()
                && fact_permits[days_to_admin_close] >= 0
                && fact_permits[days_to_admin_close] <= 365
        ),
        fact_permits[est_const_cost]
    ),
    dim_permit_type[cost_is_expected] = TRUE ()
)
```

> **The `cost_is_expected` filter is not optional.** Construction cost is
> missing-not-at-random by permit type: 87–95% of trade permits (plumbing,
> mechanical, drain) carry a placeholder string instead of a number, while new
> houses carry one 100% of the time. Remove this filter and Power BI will
> happily average a population that reports cost against one that structurally
> cannot, and return a number that looks entirely reasonable.

### Cost band column

Calculated **column** on `fact_permits` (not a measure — it is a grouping):

```dax
Cost Band =
SWITCH (
    TRUE (),
    ISBLANK ( fact_permits[est_const_cost] ), "n/a",
    fact_permits[est_const_cost] <   25000, "1. under $25k",
    fact_permits[est_const_cost] <  100000, "2. $25k-100k",
    fact_permits[est_const_cost] <  500000, "3. $100k-500k",
    fact_permits[est_const_cost] < 5000000, "4. $500k-5M",
    "5. over $5M"
)
```

Sort it by itself — the numeric prefixes give the correct order. Strip the
prefixes in the visual's display name if you prefer clean labels.

---

## 3. Visual-to-field mapping

One page, 12-column grid. Section numbers match the web version.

### Header

| Element | Type | Content |
|---|---|---|
| Title | Text box | "How long does Toronto take to approve a building permit?" |
| Correction notice | Text box | The censoring explanation. **Keep this above the charts** — it is the reason the numbers differ from the raw file. |

### KPI row — five Card visuals

| Card | Field | Format |
|---|---|---|
| Permits analysed | `[Permits]` | Whole number, thousands separator |
| Typical wait | `[Median Days to Issue]` | Whole number + " days" |
| Approved within 30 days | `[Pct Within 30 Days]` | Percentage, 0 dp |
| Worst year | `[Median Days to Issue]`, filtered `dim_date[year] = 2022` | Whole number |
| Latest | `[Median Days to Issue]`, filtered `dim_date[year] = 2025` | Whole number |

### 01 — The correction, drawn

| Property | Value |
|---|---|
| Visual | Line chart |
| X axis | `dim_date[year]` |
| Y axis | `[Median Days UNCORRECTED]` and `[Median Days to Issue]` |
| Colours | Uncorrected `#eb6834` · Corrected `#2a78d6` |
| Line width | 2 px, round join |
| Markers | On, 8 px, surface-coloured 2 px ring |
| Y axis | Start at 0, end at 40 |
| Legend | Top left |
| Data labels | **Off** — add a single text box at each line's endpoint instead |

> **One Y axis only.** Both series are in days, so they share a scale. If a
> stakeholder asks to overlay permit volume, that is a second chart — never a
> secondary axis. A dual axis invents a correlation the data does not contain,
> because the alignment of the two scales is arbitrary.

### 02 — Censoring evidence, two visuals side by side

| | Left | Right |
|---|---|---|
| Visual | Clustered column | Clustered column |
| X axis | `dim_date[year]` | `dim_date[year]` |
| Y axis | `[Pct Closed Within 1 Year]` | `[Longest Review In File]` |
| Y range | 0 – 100% | 0 – 3,600 |
| Colour | `#2a78d6` | `#2a78d6` |
| Corner radius | 3 px | 3 px |

### 03 — Districts by complexity

| Property | Value |
|---|---|
| Visual | Clustered column chart |
| X axis | `dim_geography[district_name]` |
| Legend | `dim_permit_type[permit_type]`, filtered to the three types below |
| Y axis | `[Median Days to Issue]` |
| Legend filter | Small Residential Projects · Building Additions/Alterations · New Houses |
| Colours | `#86b6ef` → `#2a78d6` → `#1c5cab` (ordinal, light to dark by complexity) |
| Data labels | On, outside end |

> The colour ramp is ordinal on purpose — complexity is an ordered variable, so
> light-to-dark on a single hue encodes it. Do **not** use three unrelated
> categorical hues here; that would throw away the ordering the reader needs.

### 04 — Cost bands

| Property | Value |
|---|---|
| Visual | Clustered column chart |
| X axis | `fact_permits[Cost Band]` |
| Y axis | `[Median Days to Issue]` |
| Colours | `#86b6ef` `#5598e7` `#2a78d6` `#1c5cab` `#104281` |
| Error bars / reference | `[P90 Days to Issue]` as a line overlay or analytics-pane constant |
| Filter | `dim_permit_type[permit_family] = "Building"` |

> The p90 for "over $5M" is about 1,036 days. Clip the axis at 60 and annotate
> the clipped value rather than letting one bar flatten the other four.

### 05 / 06 — Tables

Two Table visuals: permit types (`permit_type`, `[Median Days to Issue]`,
`[P90 Days to Issue]`, `permit_family`, `[Analysable Records]`, filtered to
≥ 500 records) and the data-quality scorecard.

---

## 4. Page-level filters

Applied to the whole page, not per visual:

| Field | Condition |
|---|---|
| `dim_date[year]` (via application date) | between 2017 and 2025 |
| `fact_permits[is_review_analysable]` | is TRUE |

**2026 is excluded deliberately.** It holds a partial year of closed permits
only — 100% of them closed within a year, and the longest review it can contain
is 208 days. Its numbers describe the extract date, not City performance.

---

## 5. Theme JSON

Save as `theme.json`, import via View → Themes → Browse.

```json
{
  "name": "Permit Review",
  "background": "#FCFCFB",
  "foreground": "#0B0B0B",
  "tableAccent": "#2A78D6",
  "dataColors": ["#2a78d6","#eb6834","#1baf7a","#eda100","#e87ba4",
                 "#008300","#4a3aa7","#e34948"],
  "good": "#0ca30c",
  "neutral": "#898781",
  "bad": "#d03b3b",
  "visualStyles": {
    "*": {
      "*": {
        "background": [{ "show": true, "color": { "solid": { "color": "#FCFCFB" } } }],
        "border": [{ "show": true, "color": { "solid": { "color": "#E1E0D9" } }, "radius": 2 }],
        "title": [{ "fontSize": 13, "fontColor": { "solid": { "color": "#0B0B0B" } } }],
        "labels": [{ "fontSize": 9, "color": { "solid": { "color": "#52514E" } } }]
      }
    }
  }
}
```

The `dataColors` order is not cosmetic. It is a colour-blind-validated
sequence — worst adjacent-pair separation ΔE 9.1 against a target of 8. Do not
reorder it, and do not add a ninth colour; fold a ninth category into "Other"
or split the visual.

---

## 6. Verification — do this before showing anyone

Rebuild is correct only if these match exactly. Values are from
`sql/02_views.sql` and `excel/permit_review_analysis.xlsx`.

| Check | Expected |
|---|---|
| `[Analysable Records]`, no filters, 2017–2025 | **145,326** |
| `[Permits]`, same | **136,241** |
| `[Median Days to Issue]`, same | **22** |
| `[Pct Within 30 Days]`, same | **62.8%** |
| `[Median Days to Issue]`, year = 2022 | **29** |
| `[Median Days to Issue]`, year = 2017 | **20** |
| `[Median Days UNCORRECTED]`, year = 2026 | **8** |
| `[Median Days to Issue]`, district = South, type = New Houses | **30.5** |

If any figure differs, the likeliest causes in order: the closure-window filter
missing from a measure, a date relationship pointing at `issued_date_key`
instead of `application_date_key`, or `cost_is_expected` dropped from a cost
measure.
