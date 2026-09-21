-- ============================================================================
-- Toronto Building Permit Review Times — star schema
-- PostgreSQL 16
--
-- Design notes (why this shape, not one flat table):
--   * One fact table holds the events. Four small dimension tables hold the
--     descriptive attributes. This is a star schema.
--   * Every row from the source survives. Quality problems are recorded as
--     boolean flags on the fact, never by deleting rows. Filtering happens in
--     views (02_views.sql) where it is visible and reversible.
--   * Grain of fact_permits: one row = one source record, identified by
--     (permit_num, revision_num, permit_type). See logs/02-dig-describe.md
--     Finding 1 for why permit_num alone is NOT unique.
-- ============================================================================

DROP SCHEMA IF EXISTS permits CASCADE;
CREATE SCHEMA permits;
SET search_path TO permits;

-- ---------------------------------------------------------------- dimensions

CREATE TABLE dim_date (
    date_key        INTEGER PRIMARY KEY,   -- yyyymmdd
    full_date       DATE        NOT NULL,
    year            SMALLINT    NOT NULL,
    quarter         SMALLINT    NOT NULL,
    month           SMALLINT    NOT NULL,
    month_name      TEXT        NOT NULL,
    year_month      TEXT        NOT NULL,
    day_of_week     TEXT        NOT NULL,
    is_weekend      BOOLEAN     NOT NULL
);
COMMENT ON TABLE dim_date IS
    'One row per calendar day spanning the full range of any date in the source.';

CREATE TABLE dim_geography (
    geography_key   INTEGER PRIMARY KEY,
    ward_grid       TEXT UNIQUE NOT NULL,  -- raw compound code, e.g. N0823
    district_code   TEXT,                  -- N / S / E / W  (C = data error)
    district_name   TEXT        NOT NULL,
    ward_code       TEXT,
    grid_code       TEXT
);
COMMENT ON TABLE dim_geography IS
    'WARD_GRID split into parts. See Finding 4: the source packs district, '
    'ward and map grid into one 5-character field.';

CREATE TABLE dim_permit_type (
    permit_type_key     INTEGER PRIMARY KEY,
    permit_type         TEXT UNIQUE NOT NULL,
    permit_family       TEXT        NOT NULL,  -- Building / Trade / Demolition
    cost_reporting_rate NUMERIC(6,4),
    cost_is_expected    BOOLEAN     NOT NULL
);
COMMENT ON COLUMN dim_permit_type.cost_is_expected IS
    'TRUE where >50%% of this type reports a construction cost. Derived from '
    'the data, not assumed. Finding 3: cost is missing-not-at-random by type, '
    'so any cost metric MUST be filtered on this flag.';

CREATE TABLE dim_status (
    status_key      INTEGER PRIMARY KEY,
    status          TEXT UNIQUE NOT NULL,
    status_group    TEXT        NOT NULL   -- Completed / Not Proceeded / In Progress
);

-- --------------------------------------------------------------------- fact

CREATE TABLE fact_permits (
    permit_sk                       BIGINT PRIMARY KEY,
    permit_num                      TEXT NOT NULL,
    revision_num                    TEXT,

    permit_type_key                 INTEGER REFERENCES dim_permit_type,
    geography_key                   INTEGER REFERENCES dim_geography,
    status_key                      INTEGER REFERENCES dim_status,
    application_date_key            INTEGER REFERENCES dim_date,
    issued_date_key                 INTEGER REFERENCES dim_date,
    completed_date_key              INTEGER REFERENCES dim_date,

    structure_type                  TEXT,
    work_type                       TEXT,

    -- measures
    days_to_issue                   INTEGER,
    days_to_admin_close             INTEGER,
    est_const_cost                  NUMERIC(16,2),
    dwelling_units_created          INTEGER,
    dwelling_units_lost             INTEGER,

    -- quality flags: findings recorded, not acted on destructively
    cost_is_sentinel                BOOLEAN NOT NULL,
    cost_is_reported                BOOLEAN NOT NULL,
    is_conditional                  BOOLEAN NOT NULL,
    flag_issued_before_applied      BOOLEAN NOT NULL,
    flag_completed_before_issued    BOOLEAN NOT NULL,
    flag_future_date                BOOLEAN NOT NULL,
    flag_unknown_district           BOOLEAN NOT NULL,
    flag_never_issued               BOOLEAN NOT NULL,
    is_review_analysable            BOOLEAN NOT NULL
);

COMMENT ON TABLE fact_permits IS
    'Grain: one row = one source permit record (permit_num + revision_num + '
    'permit_type). NOT one row per permit. Counting rows overstates permits '
    'by 11.5%% — always COUNT(DISTINCT permit_num).';

COMMENT ON COLUMN fact_permits.days_to_admin_close IS
    'ISSUED -> COMPLETED. This is NOT construction time. COMPLETED_DATE is the '
    'date the City closed the file; intervals reach 46 years. See Finding 2. '
    'Stored for transparency; must not be used as a duration metric.';

CREATE INDEX ix_fact_permit_num   ON fact_permits (permit_num);
CREATE INDEX ix_fact_type         ON fact_permits (permit_type_key);
CREATE INDEX ix_fact_geo          ON fact_permits (geography_key);
CREATE INDEX ix_fact_status       ON fact_permits (status_key);
CREATE INDEX ix_fact_applied      ON fact_permits (application_date_key);
CREATE INDEX ix_fact_analysable   ON fact_permits (is_review_analysable)
    WHERE is_review_analysable;
