-- Market Data Schema for B&R Capital Dashboard
-- Database: dashboard_market_data
--
-- Usage:
--   createdb -h localhost -p 5432 -U postgres dashboard_market_data
--   psql -h localhost -p 5432 -U postgres -d dashboard_market_data -f backend/database/schemas/market_data_schema.sql
--
-- Connection string: postgresql://postgres:****@localhost:5432/dashboard_market_data

BEGIN;

-- =============================================================================
-- 1. costar_timeseries — Normalized long-format CoStar data
-- =============================================================================
CREATE TABLE IF NOT EXISTS costar_timeseries (
    id                SERIAL PRIMARY KEY,
    geography_type    VARCHAR(20) NOT NULL,        -- 'msa' or 'submarket'
    geography_name    VARCHAR(200) NOT NULL,        -- e.g. 'Phoenix, AZ USA' or 'Camelback Corridor'
    concept           VARCHAR(200) NOT NULL,        -- e.g. 'Market Asking Rent/Unit', 'Vacancy Rate'
    date              DATE NOT NULL,                -- observation date
    value             DOUBLE PRECISION,             -- the metric value
    is_forecast       BOOLEAN DEFAULT FALSE,        -- true if date is future/forecast
    source_file       VARCHAR(500),                 -- which Excel file this came from
    created_at        TIMESTAMP DEFAULT NOW(),
    updated_at        TIMESTAMP DEFAULT NOW(),

    CONSTRAINT uq_costar_timeseries
        UNIQUE (geography_type, geography_name, concept, date)
);

CREATE INDEX IF NOT EXISTS idx_costar_geo_concept
    ON costar_timeseries (geography_name, concept);

CREATE INDEX IF NOT EXISTS idx_costar_date
    ON costar_timeseries (date);

CREATE INDEX IF NOT EXISTS idx_costar_geo_type
    ON costar_timeseries (geography_type);

-- =============================================================================
-- 2. fred_timeseries — FRED series observations
-- =============================================================================
CREATE TABLE IF NOT EXISTS fred_timeseries (
    id          SERIAL PRIMARY KEY,
    series_id   VARCHAR(50) NOT NULL,              -- e.g. 'FEDFUNDS', 'DGS10'
    date        DATE NOT NULL,
    value       DOUBLE PRECISION,
    created_at  TIMESTAMP DEFAULT NOW(),

    CONSTRAINT uq_fred_timeseries
        UNIQUE (series_id, date)
);

CREATE INDEX IF NOT EXISTS idx_fred_series
    ON fred_timeseries (series_id);

CREATE INDEX IF NOT EXISTS idx_fred_date
    ON fred_timeseries (date);

-- =============================================================================
-- 3. census_timeseries — Census Bureau annual data
-- =============================================================================
CREATE TABLE IF NOT EXISTS census_timeseries (
    id               SERIAL PRIMARY KEY,
    variable_code    VARCHAR(50) NOT NULL,          -- e.g. 'B01003_001E' (Population)
    variable_name    VARCHAR(200) NOT NULL,         -- human-readable name
    geography_id     VARCHAR(50) NOT NULL,          -- e.g. 'CBSA:38060' (Phoenix MSA)
    geography_name   VARCHAR(200) NOT NULL,
    year             INTEGER NOT NULL,
    value            DOUBLE PRECISION,
    dataset          VARCHAR(50) DEFAULT 'acs5',    -- ACS 5-Year
    created_at       TIMESTAMP DEFAULT NOW(),

    CONSTRAINT uq_census_timeseries
        UNIQUE (variable_code, geography_id, year, dataset)
);

-- =============================================================================
-- 4. fred_series_metadata — Pre-populated with 17 FRED series
-- =============================================================================
CREATE TABLE IF NOT EXISTS fred_series_metadata (
    series_id            VARCHAR(50) PRIMARY KEY,
    title                VARCHAR(500) NOT NULL,
    category             VARCHAR(100) NOT NULL,     -- 'interest_rates', 'phoenix_economic', 'national_economic'
    frequency            VARCHAR(20),               -- 'daily', 'monthly', 'quarterly'
    units                VARCHAR(100),              -- 'Percent', 'Thousands of Persons', 'Index'
    seasonal_adjustment  VARCHAR(50),
    last_updated         TIMESTAMP,
    observation_start    DATE,
    observation_end      DATE
);

-- Pre-populate the 17 tracked FRED series
INSERT INTO fred_series_metadata (series_id, title, category, frequency, units, seasonal_adjustment)
VALUES
    -- Interest Rates
    ('FEDFUNDS',    'Federal Funds Effective Rate',                  'interest_rates',    'monthly', 'Percent', 'Not Seasonally Adjusted'),
    ('DPRIME',      'Bank Prime Loan Rate',                          'interest_rates',    'monthly', 'Percent', 'Not Seasonally Adjusted'),
    ('DGS1MO',      'Market Yield on U.S. Treasury Securities at 1-Month Constant Maturity',  'interest_rates', 'daily', 'Percent', 'Not Seasonally Adjusted'),
    ('DGS3MO',      'Market Yield on U.S. Treasury Securities at 3-Month Constant Maturity',  'interest_rates', 'daily', 'Percent', 'Not Seasonally Adjusted'),
    ('DGS6MO',      'Market Yield on U.S. Treasury Securities at 6-Month Constant Maturity',  'interest_rates', 'daily', 'Percent', 'Not Seasonally Adjusted'),
    ('DGS1',        'Market Yield on U.S. Treasury Securities at 1-Year Constant Maturity',   'interest_rates', 'daily', 'Percent', 'Not Seasonally Adjusted'),
    ('DGS2',        'Market Yield on U.S. Treasury Securities at 2-Year Constant Maturity',   'interest_rates', 'daily', 'Percent', 'Not Seasonally Adjusted'),
    ('DGS5',        'Market Yield on U.S. Treasury Securities at 5-Year Constant Maturity',   'interest_rates', 'daily', 'Percent', 'Not Seasonally Adjusted'),
    ('DGS7',        'Market Yield on U.S. Treasury Securities at 7-Year Constant Maturity',   'interest_rates', 'daily', 'Percent', 'Not Seasonally Adjusted'),
    ('DGS10',       'Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity',  'interest_rates', 'daily', 'Percent', 'Not Seasonally Adjusted'),
    ('DGS20',       'Market Yield on U.S. Treasury Securities at 20-Year Constant Maturity',  'interest_rates', 'daily', 'Percent', 'Not Seasonally Adjusted'),
    ('DGS30',       'Market Yield on U.S. Treasury Securities at 30-Year Constant Maturity',  'interest_rates', 'daily', 'Percent', 'Not Seasonally Adjusted'),
    ('SOFR',        'Secured Overnight Financing Rate',              'interest_rates',    'daily',   'Percent', 'Not Seasonally Adjusted'),
    ('MORTGAGE30US','30-Year Fixed Rate Mortgage Average in the United States', 'interest_rates', 'weekly', 'Percent', 'Not Seasonally Adjusted'),

    -- Phoenix Economic
    ('PHOE004UR',   'Unemployment Rate in Phoenix-Mesa-Chandler, AZ (MSA)', 'phoenix_economic', 'monthly', 'Percent',              'Not Seasonally Adjusted'),
    ('PHOE004NA',   'All Employees: Total Nonfarm in Phoenix-Mesa-Chandler, AZ (MSA)', 'phoenix_economic', 'monthly', 'Thousands of Persons', 'Not Seasonally Adjusted'),

    -- National Economic
    ('CPIAUCSL',    'Consumer Price Index for All Urban Consumers: All Items in U.S. City Average', 'national_economic', 'monthly', 'Index 1982-1984=100', 'Seasonally Adjusted')
ON CONFLICT (series_id) DO NOTHING;

-- =============================================================================
-- 5. extraction_log — Tracks every extraction run
-- =============================================================================
CREATE TABLE IF NOT EXISTS extraction_log (
    id                  SERIAL PRIMARY KEY,
    source              VARCHAR(50) NOT NULL,       -- 'costar', 'fred', 'census'
    started_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMP,
    status              VARCHAR(20) NOT NULL DEFAULT 'running',  -- 'running', 'success', 'failed'
    records_processed   INTEGER DEFAULT 0,
    records_inserted    INTEGER DEFAULT 0,
    records_updated     INTEGER DEFAULT 0,
    error_message       TEXT,
    details             JSONB                       -- extra metadata
);

-- =============================================================================
-- Materialized View 1: costar_latest — Latest value per geography/concept
-- =============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS costar_latest AS
SELECT DISTINCT ON (geography_type, geography_name, concept)
    geography_type,
    geography_name,
    concept,
    date,
    value,
    is_forecast
FROM costar_timeseries
WHERE is_forecast = FALSE
ORDER BY geography_type, geography_name, concept, date DESC;

CREATE UNIQUE INDEX IF NOT EXISTS uidx_costar_latest
    ON costar_latest (geography_type, geography_name, concept);

-- =============================================================================
-- Materialized View 2: fred_latest — Latest value per series
-- =============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS fred_latest AS
SELECT DISTINCT ON (series_id)
    series_id,
    date,
    value
FROM fred_timeseries
ORDER BY series_id, date DESC;

CREATE UNIQUE INDEX IF NOT EXISTS uidx_fred_latest
    ON fred_latest (series_id);

COMMIT;
