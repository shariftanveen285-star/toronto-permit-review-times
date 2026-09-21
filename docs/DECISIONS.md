# Decision Log

Every non-obvious choice, why it was made, and what was rejected. Required by
the charter's traceability mandate. Newest last.

---

## D-001 — Target posting

**Date:** 2026-09-20
**Decision:** Build against *Reporting & Data Analyst (SQL / Python / Power BI)*,
Collection nc, Markham — https://to.indeed.com/aafhwxldrd7j

**Rejected:**
- Moneris Business Data Analyst — requires 3–5 yrs + 1 yr each dbt/Snowflake.
  Hard wall, not a soft preference.
- Niche Bakers Production Data Analyst — hard-requires a Bachelor's with a
  screening question attached. Tan holds an advanced diploma.

**Why this one:** explicit "self-taught candidates welcome" section naming
GitHub portfolios; counts project experience toward the 1–3 year requirement;
lists Cursor AI as a *preferred* qualification; responsibilities map 1:1 to the
planned pipeline.

---

## D-002 — Build to the profile, not the firm

**Date:** 2026-09-20
**Decision:** Tailor the *pitch* to Collection nc; keep the *asset* general.

**Why:** Employer identity could not be verified (see `00b-employer-vetting.md`)
— empty Indeed profile, no web presence, name appears truncated. Rather than
either abandoning a well-matched posting or betting weeks on an unverified
firm, we build to the requirement profile (SQL + Python + Excel + Power BI,
reporting automation, data-quality investigation, documentation), which is the
standard junior reporting-analyst profile across the GTA.

**Consequence:** if the firm evaporates, the project transfers to any other
Toronto reporting-analyst posting with zero rework. Firm-specific tailoring
(cover letter, resume bullets) costs hours, not weeks, and is regenerated per
application.

---

## D-003 — Business domain: operations / fulfillment

**Date:** 2026-09-20
**Decision:** Orders, shipments, on-time delivery, warehouses.

**Why:**
1. The posting's own language points here — "operational … reports",
   "automate … manual business processes", "improve operational efficiency".
2. It is the exact domain the ACHIEVE and DIG charter documents use for every
   worked example, so tutor lessons and the real project reinforce each other
   instead of competing for attention.

---

## D-004 — Dashboard design approach

**Date:** 2026-09-20
**Decision:** Dribbble + Figma Community for inspiration → build a **Design
System artifact** (tokens, type scale, components) → build the dashboard as an
Artifact using the `dataviz` methodology.

**Rejected — Lovable:** costs a subscription; builds a standalone app
disconnected from the validated pipeline, breaking the traceability chain; and
creates an authorship problem — "I used Lovable to build this" is a materially
weaker interview answer than "I built this", and the charter requires
personally-practiced and AI-assisted work be kept in separate ledgers.

**Rejected — Figma connector:** its tools are read-only (`get_design_context`,
`get_screenshot`, `get_variable_defs`). It is a design-to-code bridge, not a
design generator. It would only help if Tan first built mockups in Figma by
hand — a real skill, but a designer's skill, and not on this posting.

**Side benefit:** a documented design system is itself a portfolio artifact.

---

## D-005 — Design happens *after* the analysis

**Date:** 2026-09-20
**Decision:** Design research and design-system build sit at Stage 8, not now.

**Why:** the charter states every visual must support a management question. A
dashboard designed before the findings exist is a dashboard designed around
imaginary data, and gets reworked. Named risk: design is the easiest place in
this project to lose two weeks to polish while the analysis sits unfinished.

**Also noted:** the posting asks for **Power BI**. The custom dashboard is a
bonus; `dashboard/POWERBI_REBUILD.md` is what actually answers requirement T4.

---

## D-006 — Figma: connected, deferred, and a correction

**Date:** 2026-09-20
**Decision:** Figma connected and verified (authenticated as Tanveen Sharif).
Not used for this project's dashboard. Scheduled for a design-token push after
the remaining stages are complete.

**Correction to D-004.** That entry recorded the Figma connector as read-only —
"a design-to-code bridge, not a design generator." That was wrong. It was based
on the partial tool list the connector registry shows before connection. The
live connector includes write tools: `use_figma` (Figma Plugin API),
`create_new_file`, `generate_figma_design`, `generate_diagram`.

The conclusion in D-004 stands, but the reasoning in it does not. The real
reason not to rebuild this dashboard in Figma is that Figma would produce a
*picture* of a dashboard — not filterable, not hoverable, not linkable as a
working artifact. For an analyst portfolio the working version is worth more.

**Where Figma is scheduled to be used:** pushing this project's validated token
set (8 categorical colours, 2 ordinal ramps, type scale, spacing, light/dark
pairs) into a Figma variables file, as a reusable foundation for later
projects.

**Open risk:** the Figma account seat reports as `View` on a starter plan.
Write operations may be refused. To be tested before being relied on.
