# Log 04 — SQL modelling

**Target:** PostgreSQL 16. One fact table, four dimensions.

## Why a star schema and not one flat table

The source is already one wide table of 32 columns, so a flat load would have
been less work. Three reasons not to:

1. **Repetition.** Every permit-type description, district name and status
   label would repeat on all 438,949 rows.
2. **Maintenance.** Renaming a permit type becomes a mass update rather than a
   one-row edit.
3. **No home for an Unknown member.** The pattern that later fixed a real
   defect has nowhere to live in a flat table.

```
                    dim_date (18,034)
                          |
dim_geography (464) -- fact_permits (438,949) -- dim_permit_type (23)
                          |
                    dim_status (21)
```

## Grain, stated on the table itself

```sql
COMMENT ON TABLE fact_permits IS
    'Grain: one row = one source permit record (permit_num + revision_num +
     permit_type). NOT one row per permit. Counting rows overstates permits
     by 11.5% -- always COUNT(DISTINCT permit_num).';
```

The comment is deliberate. The next person to query this table will not read
`logs/02`, but they may run `\d+` — so the warning lives where they will
actually meet it.

## Referential integrity — a real decision, not a default

`dim_geography` was first built by dropping rows with a null `WARD_GRID`. Five
fact rows then had a NULL foreign key. Since every analysis view uses
`INNER JOIN`, those five were being silently dropped from every query.

The three options:

| Option | Verdict |
|---|---|
| Delete the five rows | Rejected — violates the project's flag-don't-delete rule, and makes the row count stop matching the source |
| Leave the NULL key | Rejected — silent row loss is the failure mode with no symptom |
| **Unknown member (key 0)** | **Chosen** — unmatched facts still join, and their unknown-ness is visible in the data rather than invisible |

Found by `ai/qa_reviewer.py`, not by eye, after three rounds of manual review.
Written up in `logs/06`.

## Where the filters live

**Not in the fact table.** Every source row is loaded, carrying boolean quality
flags. All exclusions live in `sql/02_views.sql`.

Two consequences, both deliberate:

- Every exclusion in the project is readable in one file.
- Relaxing one is a `WHERE`-clause edit, not a reload.

`v_permit_review` is the base view. Its three exclusions each trace to a
documented finding: not `Completed` (no review duration exists), null or
negative `days_to_issue` (impossible sequence), and future dates.

## Indexing

Five B-tree indexes on the foreign keys, plus one **partial** index:

```sql
CREATE INDEX ix_fact_analysable ON fact_permits (is_review_analysable)
    WHERE is_review_analysable;
```

Partial because 89% of rows qualify and every analysis view filters on it — the
index only needs to cover the rows anyone actually queries.

## Median in PostgreSQL

`PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ...)` — an ordered-set aggregate,
not a plain one. Worth knowing because there is no `MEDIAN()` function, and
`AVG()` is the wrong answer here: the p90 is roughly four times the median.
