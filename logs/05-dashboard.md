# Log 05 — Dashboard

**Published:** https://claude.ai/artifact/HZUdjZLgVB4JQFjzYrwqrA
**Spec for a native rebuild:** `dashboard/POWERBI_REBUILD.md`

## The structural decision

The dashboard leads with a **correction notice**, before any chart.

The temptation was to open with the KPI row. But the single most important fact
about this dataset is that its obvious trend is an artifact — and a reader who
meets the charts first has already formed the wrong impression. The notice is
the thesis, so it goes first.

The hero chart then draws both lines on the same axes: the uncorrected series
and the like-for-like one. Where they diverge *is* the finding.

## Design decisions

**Colour.** Taken from a validated palette, then verified with a runnable
colour-blindness check rather than judged by eye. The first attempt failed:

```
[FAIL] Chroma floor   below floor (reads gray): [["#898781", 0.009]]
```

Grey had been chosen for the "misleading" line — muted, deprecated, visually
subordinate. But two series people must distinguish cannot rely on a colour
that reads as grey. Replaced with orange; re-ran; passed.

Ordered categories (complexity tiers, cost bands) use an **ordinal ramp** —
one hue, light to dark — because the order is information. Unordered categories
would get distinct hues.

**Typography.** IBM Plex Sans and Plex Mono. Technical and civic rather than
generic, and the mono carries tabular figures so digits align in columns.

**Theme.** Light by default, dark behind a toggle. A dashboard opened once and
read for three minutes is a document, and documents are light. Dark themes earn
their place in tools people stare at for hours. The toggle remembers a choice.

## Two defects found by looking at the rendered page

**1. Chart text was unreadable below desktop width.** The charts are SVG scaled
to their container, so a label authored at 15px rendered near 11px on a laptop
and about 5px on a phone. Fixed by increasing type *and* setting a minimum
chart width, below which the chart scrolls horizontally instead of shrinking.
Increasing the font alone would have masked it on desktop and left it broken on
mobile.

**2. A mark that encoded nothing.** The cost chart carried a p90 tick on each
bar. Every band's p90 (85–1,036 days) sits above the 60-day axis, so all five
clipped to the same line — five identical marks at the ceiling.

Three options: raise the axis (1,036 would flatten the five median bars), add a
second axis (never — two scales invent a relationship), or remove the mark.

Removed. The exact p90 moved to the tooltip and table view, and the striking
figure — *the slowest 10% of projects over $5M wait 1,036 days* — moved into
the text above the chart, where it lands harder than a clipped tick ever could.

**A mark that is clipped in 100% of cases is worse than no mark**, because the
reader assumes it means something.

## Accessibility

- Every chart has a table-view twin; no value is reachable only by hovering
- Keyboard focus shows the same tooltip as hover
- Legend present for every multi-series chart, plus selective direct labels
- `prefers-reduced-motion` respected
- Light and dark each validated against their own surface

## Why HTML and not Power BI

Power BI Desktop was not available in the build environment. Rather than imply
a `.pbix` exists, `POWERBI_REBUILD.md` specifies the exact data model,
relationships, every DAX measure, visual-to-field mapping, theme JSON, and a
verification table of eight figures a rebuild must reproduce.

The web version and a native version are therefore provably equivalent, and the
gap is stated plainly rather than papered over.
