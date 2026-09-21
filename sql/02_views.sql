-- ============================================================================
-- Analysis views.
--
-- All filtering lives here, not in the fact table. That means every exclusion
-- is visible in one file, and any of them can be relaxed by editing a WHERE
-- clause rather than reloading data.
-- ============================================================================
SET search_path TO permits;

-- ---------------------------------------------------------------------------
-- Base view: permit records whose review duration is trustworthy.
-- Exclusions, each traceable to logs/02-dig-describe.md:
--   * status_group <> 'Completed'  -> never issued, so no review duration
--   * days_to_issue IS NULL / < 0  -> impossible sequence (Finding 5)
--   * flag_future_date             -> dates beyond today
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_permit_review AS
SELECT
    f.permit_sk,
    f.permit_num,
    f.revision_num,
    t.permit_type,
    t.permit_family,
    t.cost_is_expected,
    g.district_name,
    g.ward_code,
    g.ward_grid,
    s.status,
    s.status_group,
    da.full_date                AS application_date,
    da.year                     AS application_year,
    da.year_month               AS application_year_month,
    di.full_date                AS issued_date,
    di.year                     AS issued_year,
    f.days_to_issue,
    f.est_const_cost,
    f.cost_is_reported,
    f.is_conditional,
    f.dwelling_units_created,
    f.structure_type,
    f.work_type
FROM fact_permits f
JOIN dim_permit_type t ON t.permit_type_key      = f.permit_type_key
JOIN dim_geography   g ON g.geography_key        = f.geography_key
JOIN dim_status      s ON s.status_key           = f.status_key
JOIN dim_date       da ON da.date_key            = f.application_date_key
JOIN dim_date       di ON di.date_key            = f.issued_date_key
WHERE f.is_review_analysable;

COMMENT ON VIEW v_permit_review IS
    'Grain: one row per permit RECORD (not per permit). Use '
    'COUNT(DISTINCT permit_num) for permit counts.';


-- ---------------------------------------------------------------------------
-- Review time by application year. Median, not mean: the distribution has a
-- long right tail (p95 is roughly 13x the median), so a mean would be dragged
-- upward by a handful of extreme cases and would not describe a typical wait.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_review_by_year AS
SELECT
    application_year,
    COUNT(*)                                                    AS records,
    COUNT(DISTINCT permit_num)                                  AS permits,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY days_to_issue)::numeric, 1) AS median_days,
    ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY days_to_issue)::numeric, 1) AS p90_days,
    ROUND(AVG(days_to_issue)::numeric, 1)                       AS mean_days,
    ROUND(100.0 * AVG(CASE WHEN days_to_issue <= 30 THEN 1 ELSE 0 END), 1)
                                                                AS pct_within_30d
FROM v_permit_review
GROUP BY application_year
ORDER BY application_year;


-- ---------------------------------------------------------------------------
-- Review time by district.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_review_by_district AS
SELECT
    district_name,
    COUNT(*)                                                    AS records,
    COUNT(DISTINCT permit_num)                                  AS permits,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY days_to_issue)::numeric, 1) AS median_days,
    ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY days_to_issue)::numeric, 1) AS p90_days,
    ROUND(100.0 * AVG(CASE WHEN days_to_issue <= 30 THEN 1 ELSE 0 END), 1)
                                                                AS pct_within_30d
FROM v_permit_review
GROUP BY district_name
ORDER BY median_days DESC;


-- ---------------------------------------------------------------------------
-- Review time by permit type.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_review_by_type AS
SELECT
    permit_type,
    permit_family,
    COUNT(*)                                                    AS records,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY days_to_issue)::numeric, 1) AS median_days,
    ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY days_to_issue)::numeric, 1) AS p90_days
FROM v_permit_review
GROUP BY permit_type, permit_family
HAVING COUNT(*) >= 100          -- suppress types too small to be stable
ORDER BY median_days DESC;


-- ---------------------------------------------------------------------------
-- Cost analysis. GUARDED: cost_is_expected only.
-- Finding 3 — cost is missing-not-at-random by permit type. Trade permits do
-- not carry a construction cost, so including them would average a population
-- that reports cost against one that structurally cannot.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_cost_by_type AS
SELECT
    permit_type,
    COUNT(*)                                                    AS records,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY est_const_cost)::numeric, 0) AS median_cost,
    ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY est_const_cost)::numeric, 0) AS p90_cost,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY days_to_issue)::numeric, 1)  AS median_days
FROM v_permit_review
WHERE cost_is_expected           -- the guard
  AND cost_is_reported
  AND est_const_cost > 0
GROUP BY permit_type
HAVING COUNT(*) >= 100
ORDER BY median_cost DESC;


-- ---------------------------------------------------------------------------
-- Data quality scorecard. Published alongside the analysis, not hidden.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_data_quality AS
SELECT 'total source records'          AS metric, COUNT(*)::bigint AS value FROM fact_permits
UNION ALL SELECT 'distinct permit numbers',      COUNT(DISTINCT permit_num) FROM fact_permits
UNION ALL SELECT 'row-count overstatement',      COUNT(*) - COUNT(DISTINCT permit_num) FROM fact_permits
UNION ALL SELECT 'analysable for review time',   COUNT(*) FILTER (WHERE is_review_analysable) FROM fact_permits
UNION ALL SELECT 'never issued',                 COUNT(*) FILTER (WHERE flag_never_issued) FROM fact_permits
UNION ALL SELECT 'cost field = sentinel string', COUNT(*) FILTER (WHERE cost_is_sentinel) FROM fact_permits
UNION ALL SELECT 'cost usable',                  COUNT(*) FILTER (WHERE cost_is_reported) FROM fact_permits
UNION ALL SELECT 'issued before applied',        COUNT(*) FILTER (WHERE flag_issued_before_applied) FROM fact_permits
UNION ALL SELECT 'completed before issued',      COUNT(*) FILTER (WHERE flag_completed_before_issued) FROM fact_permits
UNION ALL SELECT 'date in the future',           COUNT(*) FILTER (WHERE flag_future_date) FROM fact_permits
UNION ALL SELECT 'unknown district code',        COUNT(*) FILTER (WHERE flag_unknown_district) FROM fact_permits
UNION ALL SELECT 'conditional permits',          COUNT(*) FILTER (WHERE is_conditional) FROM fact_permits;
