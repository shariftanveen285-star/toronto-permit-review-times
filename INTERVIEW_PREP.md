# Interview Prep

Everything here is grounded in what was actually built. No generic advice.

---

## The 90-second pitch

> I analysed how long Toronto takes to approve a building permit, using the
> City's open data — about 439,000 records going back to the 1980s.
>
> The headline finding is that the obvious answer was wrong. The raw data looks
> like approvals got 69% faster since 2017. They didn't. The file only contains
> permits the City has already closed, so recent years only show the fast ones —
> a hundred percent of 2026's permits closed within a year, because nothing
> slower could be in the file yet.
>
> When I applied the same rule to every year, the real story reversed: reviews
> got 45% *slower* between 2017 and 2022, then recovered completely. 2025 is
> statistically identical to 2017.
>
> I built it end to end — cleaned it in Excel and Power Query, modelled it in
> PostgreSQL as a star schema, tested it in Python, and built a dashboard plus
> a full Power BI rebuild spec. Every headline number reconciles across Excel,
> SQL and Python to four decimal places.

**Stop there.** Let them ask.

---

## The six numbers to memorise

| Number | What it is |
|---|---|
| **438,949 / 393,521** | Rows vs actual permits — counting rows overstates by 11.5% |
| **20 → 29 → 18** | Median days to approve: 2017, 2022, 2025 |
| **p = 0.807** | 2025 vs 2017 — statistically identical. The recovery is complete |
| **222,734** | Rows where the cost field holds a placeholder string, 50.7% of the file |
| **52,000** | Cost values a naive numeric conversion silently deletes |
| **15 passed, 1 failed** | First run of the QA agent — it found a real bug |

---

## Likely questions, with answers

### "Walk me through the project."

Use the pitch. Then: *"The part I'd point to is that I tested the obvious
answer instead of publishing it. Twice it turned out to be wrong."*

### "What was the hardest part?"

> Realising the trend was an artifact. The improving line looked completely
> plausible — it's the chart most people would ship. What gave it away was the
> record count falling every year, from 40,000 in 2017 to 4,000 in 2026. If
> applications were steady, that shouldn't happen. That made me ask what the
> file actually contains, and the answer was: only closed permits.

### "How did you know the fair comparison was fair?"

> I applied one identical rule to every year — only permits closed within 365
> days of issue. It doesn't eliminate the bias entirely, and I say so in the
> write-up. What it does is make the years comparable to each other, which the
> raw data isn't. I also excluded 2026 entirely, because it's a partial year
> with a mechanical ceiling of 208 days.

### "Why median instead of average?"

> The p90 is about four times the median. With a tail that long, the mean gets
> dragged up by a handful of extreme cases and describes nobody's actual wait.
> I report both in the tables so nothing is hidden, but the headline is the
> median.

### "Why Mann-Whitney instead of a t-test?"

> A t-test assumes roughly normal data. This distribution is heavily right-
> skewed — most permits clear in under a month, a few take years. Mann-Whitney
> compares ranks instead of means, so the shape doesn't break it.

### "Tell me about a time you caught a data problem." ← **your strongest answer**

> Four, in one dataset, and none of them threw an error.
>
> The cost column had a placeholder string in half the rows — literally "DO NOT
> UPDATE OR DELETE THIS INFO FIELD", a note between City staff published in a
> currency field. And it wasn't random: 95% of mechanical permits had it, 0% of
> new-house permits. So it's missing-not-at-random — averaging cost across all
> permit types compares a group that reports cost against one that structurally
> can't, and the answer looks perfectly reasonable.
>
> The one I'd highlight is smaller. 52,000 cost values are written with a comma,
> like "50,000". If you convert that column to a number before stripping the
> commas, every one becomes blank. No error, no warning — a quarter of your
> usable cost data, gone. Two steps, and the order matters more than anything
> else in the workbook.

### "How do you know your numbers are right?"

> I computed every headline figure three independent ways — Excel formulas,
> SQL, and pandas — and they reconcile to four decimal places. There's a
> Validation tab in the workbook showing all three side by side.
>
> That doesn't prove the analysis is right; all three could share a wrong
> assumption, and I wrote that caveat into the sheet. It proves there's no
> typo, no broken formula, no copy-paste error.

### "Do you use AI? How?"

> Yes, and the design decision matters more than the fact.
>
> I built a tool that answers plain-English questions about the data. The
> obvious way is to hand the question and the data to a model. That version
> makes up numbers in confident prose, which is the worst possible failure for
> an analyst tool.
>
> So mine can't. The model never touches the database. A question gets matched
> to one of six human-written, reviewed queries, PostgreSQL computes the
> numbers, and the model gets handed finished numbers and writes two sentences.
> Every answer prints the SQL underneath it. Ask it something outside the six
> and it refuses instead of improvising.
>
> I also built an automated QA agent — sixteen checks that re-run every
> assumption. Almost none of it is a model, deliberately: a quality check has
> to give the same answer every time, and asking a model "does this look right"
> doesn't. **An AI that grades its own homework isn't a safety net.**

### "Did your AI actually find anything?"

> Yes. First run: fifteen passed, one failed. Five rows had no geography key,
> so every view was silently dropping them from every query — no error, just a
> total that's quietly short.
>
> I traced them: five cancelled permits with no ward code in the source. Zero
> impact on any published figure, because cancelled permits have no review
> duration anyway. I fixed the structure anyway, with an Unknown member in the
> dimension. The impact was zero *this month*. Next refresh the unmatched rows
> might not all be cancelled, and the failure mode is silent undercounting.

### "What's a star schema and why use one?"

> One fact table holding the events — one row per permit record — surrounded by
> small lookup tables for dates, places, permit types and statuses.
>
> The alternative is one flat wide table. That duplicates every description on
> every row, makes a rename a mass update, and gives you no clean place to put
> an Unknown member. The star keeps the facts thin and the descriptions in one
> place each.

### "What would you do differently?"

> Two things.
>
> I'd ask the City for permit status history up front. The one field that would
> let me answer *why* a permit was slow — a hold or resubmission log — doesn't
> exist in this extract, so causation is untestable. I'd rather know that on
> day one.
>
> And I over-generalised once. I tested South against East on simple permits,
> found no difference, and wrote that there was no district gap. There is —
> West runs 20 days against everyone else's 15. I'd tested two districts and
> claimed four. It's corrected in the log rather than quietly edited, because
> the mistake is instructive.

### "What are the limitations?"

Rehearse this — volunteering limits reads as confidence, not weakness.

> Four. The closure correction reduces the sampling bias but doesn't eliminate
> it. Causation is untestable — there's no staffing, workload or hold-reason
> field. Cost analysis only covers building permits, because trade permits
> don't report a cost. And the builder field is 95% empty, so anything about
> supplier performance is out of scope.

### "Why should we hire you without analyst experience?"

> Two end-to-end projects where the interesting part was catching what the data
> got wrong. In this one I found four defects that produced no error message,
> reversed two conclusions by testing them, built an automated checker that
> found a fifth, and reconciled every headline number across three tools.
>
> I'd rather be judged on that than on a job title.

---

## Questions to ask them

1. When a number in a report turns out to be wrong, what happens next — is
   there a process, or does it depend who notices?
2. How much of the reporting is still manual? Where would automation pay back
   fastest?
3. Who reads the reports I'd be building, and what decision do they make with
   them?
4. How is AI actually used on the team today — and where has it been decided
   *not* to use it?
5. What does good look like at six months?

---

## Traps to avoid

**Don't claim SQL Server.** The project uses PostgreSQL. The dialect
differences are documented. Claiming SQL Server collapses in a technical screen.

**Don't imply a `.pbix` exists.** Say plainly: *"Power BI Desktop wasn't
available, so I built an equivalent dashboard and wrote a full rebuild spec —
data model, every DAX measure, visual-to-field mapping, and a verification
table so a rebuild can be proven correct."* That's a stronger answer than a
file would have been.

**Don't oversell the AI layer.** It routes, checks, phrases and schedules. It
doesn't decide. Every number was computed by SQL, Excel or pandas.

**Don't say "the data was messy" and stop.** Name a specific defect, its size,
and what it would have broken. Specificity is the whole signal.

---

## After you can answer these unaided

Move each item in `docs/01-requirement-evidence-matrix.md` from `VALIDATED` to
`DEFENSIBLE`. That status isn't granted by building the thing — it's granted
when you can explain it cold.
