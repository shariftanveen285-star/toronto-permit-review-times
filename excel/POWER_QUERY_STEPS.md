# Power Query — Applied Steps and M Code

Reproduces the cleaning in Excel, with no Python and no database.

Every rule below traces to a finding in `logs/02-dig-describe.md`. This is not
generic tidying — each step exists because something specific was found in the
data.

**To use:** Excel → Data → Get Data → Launch Power Query Editor → New Source →
Blank Query → Home → Advanced Editor → paste. Change `Source` to your own path.

---

## Applied Steps, in order

| # | Step | Why |
|---|---|---|
| 1 | Source | Load the raw CSV, UTF-8, comma-delimited |
| 2 | Promoted Headers | First row holds column names |
| 3 | Removed Other Columns | Keep 12 of 32. Narrow early — it is faster and forces a decision about every column |
| 4 | Changed Type | Dates to `date`. Cost stays **text** on purpose — see step 6 |
| 5 | Replaced Sentinel | `DO NOT UPDATE OR DELETE THIS INFO FIELD` → null. **Finding 3** |
| 6 | Removed Thousands Separators | Strip `,` and `$` *before* converting to number. **Finding 3** — skipping this silently destroys ~52,000 values |
| 7 | Changed Type — Cost | Now safe to convert to `number` |
| 8 | Nulled Non-Positive Cost | Zero and negative costs → null. Not deleted |
| 9 | Split WARD_GRID | Into district letter, ward, grid. **Finding 4** |
| 10 | Added District Name | Letter → name. Anything else → `"Unknown"` |
| 11 | Added Permit Family | Building / Trade / Demolition |
| 12 | Added Status Group | Completed / Not Proceeded / In Progress |
| 13 | Added Days To Issue | `ISSUED − APPLICATION`, in days |
| 14 | Added Days To Admin Close | `COMPLETED − ISSUED`. **Named to prevent misuse.** Finding 2: this is NOT build time |
| 15 | Added Quality Flags | Impossible sequences flagged, **not deleted** |
| 16 | Added Is Review Analysable | One flag combining every condition for a trustworthy review duration |

**The principle, repeated because it is the point: flag, do not delete.** Every
source row survives. Filtering happens later, visibly, where a reviewer can see
and reverse it.

---

## M code

Paste whole into the Advanced Editor.

```m
let
    Source = Csv.Document(
        File.Contents("C:\data\Cleared Building Permits since 2017.csv"),
        [Delimiter = ",", Columns = 32, Encoding = 65001,
         QuoteStyle = QuoteStyle.Csv]
    ),

    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),

    // Step 3 — keep only what is needed
    KeptColumns = Table.SelectColumns(PromotedHeaders, {
        "PERMIT_NUM", "REVISION_NUM", "PERMIT_TYPE", "STRUCTURE_TYPE", "WORK",
        "WARD_GRID", "APPLICATION_DATE", "ISSUED_DATE", "COMPLETED_DATE",
        "STATUS", "EST_CONST_COST", "DWELLING_UNITS_CREATED"
    }),

    // Step 4 — cost deliberately left as text until it has been repaired
    TypedDates = Table.TransformColumnTypes(KeptColumns, {
        {"APPLICATION_DATE", type date},
        {"ISSUED_DATE", type date},
        {"COMPLETED_DATE", type date},
        {"EST_CONST_COST", type text},
        {"DWELLING_UNITS_CREATED", Int64.Type}
    }),

    // Step 5 — FINDING 3: a system placeholder in a currency column,
    // present on 222,734 of 438,949 rows (50.7%).
    ClearedSentinel = Table.ReplaceValue(
        TypedDates,
        "DO NOT UPDATE OR DELETE THIS INFO FIELD",
        null, Replacer.ReplaceValue, {"EST_CONST_COST"}
    ),

    // Step 6 — FINDING 3: ~52,000 values are written "50,000".
    // Converting to number BEFORE this step discards every one of them
    // silently. This single step is the difference between 146,490 and
    // 198,439 usable cost values.
    StrippedFormatting = Table.TransformColumns(
        ClearedSentinel,
        {{"EST_CONST_COST", each
            if _ = null then null
            else Text.Replace(Text.Replace(Text.Trim(_), ",", ""), "$", ""),
          type nullable text}}
    ),

    CostToNumber = Table.TransformColumnTypes(
        StrippedFormatting, {{"EST_CONST_COST", type nullable number}}
    ),

    // Step 8 — implausible, so null. Not deleted: the row still matters
    // for every non-cost measure.
    NulledBadCost = Table.TransformColumns(
        CostToNumber,
        {{"EST_CONST_COST", each if _ = null or _ <= 0 then null else _,
          type nullable number}}
    ),

    // Step 9 — FINDING 4: WARD_GRID packs three facts into 5 characters.
    SplitDistrict = Table.AddColumn(NulledBadCost, "DistrictCode",
        each if [WARD_GRID] = null then null else Text.Start([WARD_GRID], 1),
        type nullable text),
    SplitWard = Table.AddColumn(SplitDistrict, "WardCode",
        each if [WARD_GRID] = null then null else Text.Middle([WARD_GRID], 1, 2),
        type nullable text),
    SplitGrid = Table.AddColumn(SplitWard, "GridCode",
        each if [WARD_GRID] = null then null else Text.Middle([WARD_GRID], 3, 2),
        type nullable text),

    // Step 10 — 'C' appears on 3 rows of 438,949. Almost certainly a typo,
    // so it lands in Unknown rather than being silently mapped somewhere.
    AddedDistrictName = Table.AddColumn(SplitGrid, "DistrictName",
        each if [DistrictCode] = "N" then "North"
        else if [DistrictCode] = "S" then "South"
        else if [DistrictCode] = "E" then "East"
        else if [DistrictCode] = "W" then "West"
        else "Unknown", type text),

    // Step 11 — FINDING 3: cost reporting splits cleanly on this line.
    AddedFamily = Table.AddColumn(AddedDistrictName, "PermitFamily",
        each if List.Contains({"Plumbing(PS)", "Mechanical(MS)",
                               "Drain and Site Service", "Designated Structures",
                               "Electrical(ES)"}, [PERMIT_TYPE]) then "Trade"
        else if Text.Contains([PERMIT_TYPE] ?? "", "Demolition") then "Demolition"
        else "Building", type text),

    AddedStatusGroup = Table.AddColumn(AddedFamily, "StatusGroup",
        each if List.Contains({"Closed", "Closed - Dormant"}, [STATUS])
                then "Completed"
        else if List.Contains({"Cancelled", "Refused", "Abandoned",
                               "Superseded"}, [STATUS]) then "Not Proceeded"
        else "In Progress", type text),

    // Step 13 — the defensible cycle time.
    AddedDaysToIssue = Table.AddColumn(AddedStatusGroup, "DaysToIssue",
        each if [ISSUED_DATE] = null or [APPLICATION_DATE] = null then null
        else Duration.Days([ISSUED_DATE] - [APPLICATION_DATE]),
        type nullable number),

    // Step 14 — FINDING 2: named "AdminClose", never "BuildTime".
    // COMPLETED_DATE is when the City closed the file. Intervals reach
    // 17,097 days (46 years). The column name is the guardrail.
    AddedDaysToAdminClose = Table.AddColumn(AddedDaysToIssue, "DaysToAdminClose",
        each if [COMPLETED_DATE] = null or [ISSUED_DATE] = null then null
        else Duration.Days([COMPLETED_DATE] - [ISSUED_DATE]),
        type nullable number),

    // Step 15 — flags, not deletions.
    FlagIssuedBeforeApplied = Table.AddColumn(AddedDaysToAdminClose,
        "FlagIssuedBeforeApplied",
        each [DaysToIssue] <> null and [DaysToIssue] < 0, type logical),

    FlagFutureDate = Table.AddColumn(FlagIssuedBeforeApplied, "FlagFutureDate",
        each ([COMPLETED_DATE] <> null and [COMPLETED_DATE] > Date.From(DateTime.LocalNow()))
          or ([APPLICATION_DATE] <> null and [APPLICATION_DATE] > Date.From(DateTime.LocalNow())),
        type logical),

    FlagNeverIssued = Table.AddColumn(FlagFutureDate, "FlagNeverIssued",
        each [ISSUED_DATE] = null, type logical),

    // Step 16 — every condition for a trustworthy review duration, in one flag.
    AddedIsAnalysable = Table.AddColumn(FlagNeverIssued, "IsReviewAnalysable",
        each [DaysToIssue] <> null
         and [DaysToIssue] >= 0
         and [StatusGroup] = "Completed"
         and [FlagFutureDate] = false,
        type logical)
in
    AddedIsAnalysable
```

---

## Two steps that matter more than they look

**Step 6, before step 7.** Converting cost to a number before stripping commas
loses about 52,000 real values. Power Query reports no error — the cells simply
become null. The order of these two steps is worth more than every formatting
choice in the workbook.

**Step 14's column name.** Calling it `DaysToAdminClose` instead of
`DaysToComplete` is a deliberate control. A future analyst who sees
"DaysToComplete" will use it as build time and be wrong by decades. The name is
the warning, carried on the data itself rather than in a document nobody opens.

---

## Not done here, and why

**The fair-window filter** (`DaysToAdminClose ≤ 365`) is *not* in this query.

It is an analytical choice that corrects for the censoring bias in Finding A,
not a data-cleaning rule. Cleaning repairs what is wrong with the data;
analysis decides what question is being asked. Mixing the two buries a
significant analytical decision inside a transformation step where no reviewer
would find it.

It is applied in the SQL views and on the workbook's Data sheet, where it is
visible and can be changed.
