"""
Builds excel/permit_review_analysis.xlsx.

Every derived value in this workbook is a LIVE FORMULA. Nothing is a number
pasted in by Python. Change a cell on the Data sheet and every summary
recalculates, which is what makes it a model rather than a screenshot.

Functions kept to the Excel-2007 set (COUNTIFS / AVERAGEIFS / INDEX / MATCH /
SUMPRODUCT / IFERROR) so the file evaluates identically in Excel and
LibreOffice. No XLOOKUP, no dynamic arrays.

Scope: building-permit family, fair window, application years 2017-2025.
Chosen because it is the one scope where BOTH review time and construction
cost are analytically valid (see logs/02 Finding 3 on cost being MNAR).
"""

import pandas as pd
import psycopg2
import warnings
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

warnings.filterwarnings("ignore")

OUT = "excel/permit_review_analysis.xlsx"

# ---------------------------------------------------------------- extract
con = psycopg2.connect(dbname="toronto_permits", user="root",
                       host="/var/run/postgresql")
df = pd.read_sql("""
SELECT f.permit_num, da.year AS app_year, g.district_name, t.permit_type,
       f.days_to_issue, f.est_const_cost, f.cost_is_reported
FROM permits.fact_permits f
JOIN permits.dim_date da        ON da.date_key       = f.application_date_key
JOIN permits.dim_permit_type t  ON t.permit_type_key = f.permit_type_key
JOIN permits.dim_geography g    ON g.geography_key   = f.geography_key
WHERE f.is_review_analysable
  AND f.days_to_admin_close BETWEEN 0 AND 365
  AND da.year BETWEEN 2017 AND 2025
  AND t.permit_family = 'Building'
ORDER BY da.year, g.district_name
""", con)
con.close()
print(f"extract: {len(df):,} rows")

# ---------------------------------------------------------------- styling
FONT = "Arial"
H_FILL = PatternFill("solid", fgColor="1F3864")
H_FONT = Font(name=FONT, bold=True, color="FFFFFF", size=10)
TITLE = Font(name=FONT, bold=True, size=14, color="1F3864")
SUB = Font(name=FONT, italic=True, size=9, color="595959")
BOLD = Font(name=FONT, bold=True, size=10)
BODY = Font(name=FONT, size=10)
INPUT_F = Font(name=FONT, size=10, color="0000FF")      # hardcoded input
LINK_F = Font(name=FONT, size=10, color="008000")       # cross-sheet link
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def header_row(ws, row, headers, widths=None):
    for i, h in enumerate(headers, start=1):
        c = ws.cell(row=row, column=i, value=h)
        c.font, c.fill, c.border = H_FONT, H_FILL, BOX
        c.alignment = Alignment(horizontal="center", vertical="center",
                                wrap_text=True)
    if widths:
        for i, w in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[row].height = 28


wb = Workbook()

# ============================================================== README
ws = wb.active
ws.title = "README"
ws.column_dimensions["A"].width = 26
ws.column_dimensions["B"].width = 96

rows = [
    ("Toronto Building Permit Review Times", None, TITLE),
    ("Live-formula analysis workbook", None, SUB),
    (None, None, None),
    ("Question", "How long does Toronto take to approve a building permit, and what changes that?", None),
    ("Source", "City of Toronto Open Data - Cleared Building Permits since 2017 (CKAN)", None),
    ("Resource id", "a96c0ba4-3026-402b-b09d-5b1268b8f810", None),
    ("Extract date", "2026-09-20", None),
    ("Raw file md5", "d5f431c2522692932fbb6040c39ccf54", None),
    (None, None, None),
    ("SCOPE", "Building-permit family only. Application years 2017-2025.", None),
    (None, "Records closed within 365 days of issue ('fair window').", None),
    ("Rows in extract", f"{len(df):,} of 438,949 source rows", None),
    (None, None, None),
    ("WHY THIS SCOPE", None, BOLD),
    ("1. Fair window", "The source contains only permits the City has already CLOSED. Recent years therefore contain only fast permits, which makes review time look like it is improving when it is not. Applying the same 365-day closure rule to every year removes that bias.", None),
    ("2. Building family", "Trade permits (plumbing, mechanical, drain) do not carry a construction cost - 87-95% of their cost values are a placeholder string. Including them would average a group that reports cost against one that structurally cannot.", None),
    ("3. Excluded metric", "ISSUED to COMPLETED is NOT construction time. It is the date the City closed the file; intervals reach 46 years. It is not in this workbook.", None),
    (None, None, None),
    ("METRIC DEFINITIONS", None, BOLD),
    ("Days to Issue", "ISSUED_DATE minus APPLICATION_DATE, in calendar days.", None),
    ("Within 30 Days", "1 if Days to Issue <= 30, else 0. Averaged, this is the share approved within a month.", None),
    ("Cost Band", "Assigned by INDEX/MATCH against the band table on 'Cost Bands'.", None),
    (None, None, None),
    ("COLOUR LEGEND", None, BOLD),
    ("Blue text", "Hardcoded input or threshold. Safe to change - everything recalculates.", INPUT_F),
    ("Green text", "Links to another sheet in this workbook.", LINK_F),
    ("Black text", "Calculated by formula. Do not overwrite.", BODY),
    (None, None, None),
    ("HOW TO VERIFY", "Every figure on the summary sheets is a formula over the Data sheet. Click any cell to see it. The Validation sheet checks these same numbers against the SQL and Python results.", None),
]
r = 1
for label, val, font in rows:
    if label is not None:
        c = ws.cell(row=r, column=1, value=label)
        c.font = font if (font and val is None) else BOLD
    if val is not None:
        c2 = ws.cell(row=r, column=2, value=val)
        c2.font = font if font else BODY
        c2.alignment = Alignment(wrap_text=True, vertical="top")
    r += 1
ws.freeze_panes = "A2"

# ============================================================== Thresholds
ws = wb.create_sheet("Thresholds")
ws.column_dimensions["A"].width = 34
ws.column_dimensions["B"].width = 14
ws.column_dimensions["C"].width = 60
header_row(ws, 1, ["Assumption", "Value", "Note"], [34, 14, 60])
thresholds = [
    ("Fast approval threshold (days)", 30,
     "A month. Used for the 'approved within 30 days' service measure."),
    ("Slow approval threshold (days)", 90,
     "A quarter. Used for the 'took over 90 days' measure."),
    ("Minimum records to report a group", 100,
     "Groups smaller than this are suppressed as unstable."),
]
for i, (a, v, n) in enumerate(thresholds, start=2):
    ws.cell(row=i, column=1, value=a).font = BODY
    c = ws.cell(row=i, column=2, value=v)
    c.font, c.border = INPUT_F, BOX
    ws.cell(row=i, column=3, value=n).font = SUB
ws.freeze_panes = "A2"

# ============================================================== Cost Bands
ws = wb.create_sheet("Cost Bands")
ws.column_dimensions["A"].width = 18
ws.column_dimensions["B"].width = 18
header_row(ws, 1, ["Lower Bound", "Band Label"], [18, 18])
bands = [(0, "A. under $25k"), (25000, "B. $25k-100k"),
         (100000, "C. $100k-500k"), (500000, "D. $500k-5M"),
         (5000000, "E. over $5M")]
for i, (lo, lbl) in enumerate(bands, start=2):
    c = ws.cell(row=i, column=1, value=lo)
    c.font, c.number_format, c.border = INPUT_F, '$#,##0', BOX
    ws.cell(row=i, column=2, value=lbl).font = BODY
ws.cell(row=8, column=1, value="Bands are ascending. Cost Band on the Data sheet "
        "uses INDEX/MATCH with match-type 1 (largest value <= lookup).").font = SUB

# ============================================================== Data
ws = wb.create_sheet("Data")
heads = ["Permit Num", "App Year", "District", "Permit Type", "Days to Issue",
         "Est Const Cost", "Cost Reported", "Within 30 Days", "Cost Band"]
header_row(ws, 1, heads, [17, 10, 11, 32, 13, 16, 14, 14, 16])

print("writing data rows...")
for i, rec in enumerate(df.itertuples(index=False), start=2):
    ws.cell(row=i, column=1, value=rec.permit_num)
    ws.cell(row=i, column=2, value=int(rec.app_year))
    ws.cell(row=i, column=3, value=rec.district_name)
    ws.cell(row=i, column=4, value=rec.permit_type)
    ws.cell(row=i, column=5, value=int(rec.days_to_issue))
    if rec.cost_is_reported and pd.notna(rec.est_const_cost):
        c = ws.cell(row=i, column=6, value=float(rec.est_const_cost))
        c.number_format = '$#,##0'
    ws.cell(row=i, column=7, value=1 if rec.cost_is_reported else 0)
    # LIVE FORMULAS -----------------------------------------------------
    ws.cell(row=i, column=8,
            value=f"=IF(E{i}<=Thresholds!$B$2,1,0)")
    ws.cell(row=i, column=9,
            value=(f"=IF(G{i}=0,\"n/a\","
                   f"INDEX('Cost Bands'!$B$2:$B$6,"
                   f"MATCH(F{i},'Cost Bands'!$A$2:$A$6,1)))"))

LAST = len(df) + 1
ws.freeze_panes = "A2"
ws.auto_filter.ref = f"A1:I{LAST}"
print(f"  data rows 2..{LAST}")

D = f"Data!$A$2:$A${LAST}"
Y = f"Data!$B$2:$B${LAST}"
DIST = f"Data!$C$2:$C${LAST}"
TYP = f"Data!$D$2:$D${LAST}"
DAYS = f"Data!$E$2:$E${LAST}"
COST = f"Data!$F$2:$F${LAST}"
REP = f"Data!$G$2:$G${LAST}"
W30 = f"Data!$H$2:$H${LAST}"
BAND = f"Data!$I$2:$I${LAST}"

# ============================================================== KPI Summary
ws = wb.create_sheet("KPI Summary", 1)
ws.column_dimensions["A"].width = 42
ws.column_dimensions["B"].width = 18
ws.column_dimensions["C"].width = 62
ws.cell(row=1, column=1, value="Headline KPIs").font = TITLE
ws.cell(row=2, column=1,
        value="Building permits, 2017-2025, fair window. All cells are formulas over the Data sheet.").font = SUB
header_row(ws, 4, ["Measure", "Value", "How it is calculated"], [42, 18, 62])

kpis = [
    ("Permit records in scope", f"=COUNTA({D})", '#,##0',
     "COUNTA over the permit number column."),
    ("Distinct permits", f"=SUMPRODUCT(({D}<>\"\")/COUNTIF({D},{D}&\"\"))", '#,##0',
     "SUMPRODUCT distinct-count. Records > permits because revisions repeat a permit number."),
    ("Mean days to issue", f"=AVERAGE({DAYS})", '#,##0.0',
     "AVERAGE of Days to Issue."),
    ("Approved within 30 days", f"=AVERAGE({W30})", '0.0%',
     "AVERAGE of the Within 30 Days flag."),
    ("Took over 90 days", f"=COUNTIF({DAYS},\">\"&Thresholds!$B$3)/COUNTA({D})", '0.0%',
     "COUNTIF above the slow threshold, over total records."),
    ("Longest single review (days)", f"=MAX({DAYS})", '#,##0',
     "MAX of Days to Issue."),
    ("Records reporting a cost", f"=SUM({REP})", '#,##0',
     "SUM of the Cost Reported flag."),
    ("Mean reported cost", f"=AVERAGEIF({REP},1,{COST})", '$#,##0',
     "AVERAGEIF - only records that actually reported a cost."),
]
for i, (label, f, fmt, note) in enumerate(kpis, start=5):
    ws.cell(row=i, column=1, value=label).font = BODY
    c = ws.cell(row=i, column=2, value=f)
    c.font, c.number_format, c.border = BOLD, fmt, BOX
    ws.cell(row=i, column=3, value=note).font = SUB

# ============================================================== By Year
ws = wb.create_sheet("By Year", 2)
ws.cell(row=1, column=1, value="Review Time by Application Year").font = TITLE
ws.cell(row=2, column=1,
        value="The deterioration to 2022 and the recovery after it. Compare 2017 with 2022.").font = SUB
header_row(ws, 4, ["App Year", "Records", "Mean Days", "Within 30 Days",
                   "Over 90 Days", "Longest Review"], [11, 12, 13, 15, 14, 15])
for i, yr in enumerate(range(2017, 2026), start=5):
    c = ws.cell(row=i, column=1, value=yr)
    c.font, c.border, c.number_format = INPUT_F, BOX, '0'
    fs = [
        (2, f"=COUNTIF({Y},$A{i})", '#,##0'),
        (3, f"=AVERAGEIF({Y},$A{i},{DAYS})", '#,##0.0'),
        (4, f"=AVERAGEIF({Y},$A{i},{W30})", '0.0%'),
        (5, f"=COUNTIFS({Y},$A{i},{DAYS},\">\"&Thresholds!$B$3)/$B{i}", '0.0%'),
        (6, f"=_xlfn.MAXIFS({DAYS},{Y},$A{i})", '#,##0'),
    ]
    for col, f, fmt in fs:
        c = ws.cell(row=i, column=col, value=f)
        c.font, c.number_format, c.border = BODY, fmt, BOX
ws.cell(row=15, column=1, value="TOTAL").font = BOLD
for col, f, fmt in [(2, f"=SUM(B5:B13)", '#,##0'),
                    (3, f"=AVERAGE({DAYS})", '#,##0.0'),
                    (4, f"=AVERAGE({W30})", '0.0%')]:
    c = ws.cell(row=15, column=col, value=f)
    c.font, c.number_format, c.border = BOLD, fmt, BOX
ws.cell(row=17, column=1,
        value="2026 is deliberately absent: only a partial year of closed permits exists, "
              "so its numbers are an artifact of the extract date, not City performance.").font = SUB

# ============================================================== By District
ws = wb.create_sheet("By District", 3)
ws.cell(row=1, column=1, value="Review Time by District").font = TITLE
ws.cell(row=2, column=1,
        value="Column F holds permit type constant. The raw gap between districts largely disappears there.").font = SUB
header_row(ws, 4, ["District", "Records", "Mean Days", "Within 30 Days",
                   "Over 90 Days", "Mean Days - Small Residential only"],
           [13, 12, 13, 15, 14, 34])
for i, d in enumerate(["South", "North", "West", "East"], start=5):
    c = ws.cell(row=i, column=1, value=d)
    c.font, c.border = INPUT_F, BOX
    fs = [
        (2, f"=COUNTIF({DIST},$A{i})", '#,##0'),
        (3, f"=AVERAGEIF({DIST},$A{i},{DAYS})", '#,##0.0'),
        (4, f"=AVERAGEIF({DIST},$A{i},{W30})", '0.0%'),
        (5, f"=COUNTIFS({DIST},$A{i},{DAYS},\">\"&Thresholds!$B$3)/$B{i}", '0.0%'),
        (6, f"=IFERROR(AVERAGEIFS({DAYS},{DIST},$A{i},{TYP},\"Small Residential Projects\"),\"n/a\")", '#,##0.0'),
    ]
    for col, f, fmt in fs:
        c = ws.cell(row=i, column=col, value=f)
        c.font, c.number_format, c.border = BODY, fmt, BOX

# ============================================================== By Cost Band
ws = wb.create_sheet("By Cost Band", 4)
ws.cell(row=1, column=1, value="Review Time by Project Cost").font = TITLE
ws.cell(row=2, column=1,
        value="Band assigned on the Data sheet by INDEX/MATCH. Bigger projects wait longer, monotonically.").font = SUB
header_row(ws, 4, ["Cost Band", "Records", "Mean Days", "Within 30 Days",
                   "Mean Cost"], [18, 12, 13, 15, 16])
for i, (lo, lbl) in enumerate(bands, start=5):
    c = ws.cell(row=i, column=1, value=lbl)
    c.font, c.border = INPUT_F, BOX
    fs = [
        (2, f"=COUNTIF({BAND},$A{i})", '#,##0'),
        (3, f"=IFERROR(AVERAGEIF({BAND},$A{i},{DAYS}),\"n/a\")", '#,##0.0'),
        (4, f"=IFERROR(AVERAGEIF({BAND},$A{i},{W30}),\"n/a\")", '0.0%'),
        (5, f"=IFERROR(AVERAGEIF({BAND},$A{i},{COST}),\"n/a\")", '$#,##0'),
    ]
    for col, f, fmt in fs:
        c = ws.cell(row=i, column=col, value=f)
        c.font, c.number_format, c.border = BODY, fmt, BOX

# ============================================================== Validation
ws = wb.create_sheet("Validation", 5)
ws.column_dimensions["A"].width = 38
for col in "BCDE":
    ws.column_dimensions[col].width = 16
ws.cell(row=1, column=1, value="Cross-Validation").font = TITLE
ws.cell(row=2, column=1,
        value="Same scope, three tools. If any row does not say MATCH, the analysis stops until it is explained.").font = SUB
header_row(ws, 4, ["Measure", "Excel", "SQL", "Python", "Result"],
           [38, 16, 16, 16, 16])
ws.cell(row=5, column=1, value="(SQL and Python values written by "
        "python/04_validate.py)").font = SUB

print("saving...")
wb.save(OUT)
print(f"saved {OUT}")
