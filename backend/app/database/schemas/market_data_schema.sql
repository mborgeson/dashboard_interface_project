-- ============================================================================
-- Market Data Database Schema
-- Database: dashboard_market_data (port 5432)
-- ============================================================================
-- Setup:
--   createdb -h localhost -p 5432 -U postgres dashboard_market_data
--   psql -h localhost -p 5432 -U postgres -d dashboard_market_data -f market_data_schema.sql
-- ============================================================================

-- 1. CoStar time-series (normalized long format)
CREATE TABLE IF NOT EXISTS costar_timeseries (
    id              BIGSERIAL PRIMARY KEY,
    geography_name  TEXT NOT NULL,          -- e.g. "Phoenix - AZ USA" or "Phoenix - AZ USA - Tempe"
    geography_type  TEXT NOT NULL,          -- 'Metro' or 'Submarket'
    geography_code  TEXT,                   -- e.g. "G2-38060" or "APT-1-11286"
    concept         TEXT NOT NULL,          -- e.g. "Market Asking Rent/Unit", "Vacancy Rate"
    date            DATE NOT NULL,          -- Quarter start date (Q1=Jan 1, Q2=Apr 1, etc.)
    value           DOUBLE PRECISION,
    is_forecast     BOOLEAN DEFAULT FALSE,
    source_file     TEXT,
    imported_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (geography_name, concept, date)
);

CREATE INDEX IF NOT EXISTS idx_costar_geo_concept ON costar_timeseries (geography_name, concept);
CREATE INDEX IF NOT EXISTS idx_costar_date ON costar_timeseries (date DESC);
CREATE INDEX IF NOT EXISTS idx_costar_type ON costar_timeseries (geography_type);
CREATE INDEX IF NOT EXISTS idx_costar_concept ON costar_timeseries (concept);

-- 2. FRED time-series
CREATE TABLE IF NOT EXISTS fred_timeseries (
    id          BIGSERIAL PRIMARY KEY,
    series_id   TEXT NOT NULL,              -- e.g. "FEDFUNDS", "DGS10"
    date        DATE NOT NULL,
    value       DOUBLE PRECISION,
    imported_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (series_id, date)
);

CREATE INDEX IF NOT EXISTS idx_fred_series_date ON fred_timeseries (series_id, date DESC);

-- 3. Census Bureau time-series
CREATE TABLE IF NOT EXISTS census_timeseries (
    id              BIGSERIAL PRIMARY KEY,
    variable_code   TEXT NOT NULL,          -- e.g. "B01003_001E" (population)
    variable_name   TEXT,                   -- Human-readable name
    geography       TEXT NOT NULL,          -- e.g. "Phoenix-Mesa-Chandler, AZ Metro Area"
    geography_code  TEXT,                   -- CBSA code
    year            INT NOT NULL,
    value           DOUBLE PRECISION,
    dataset         TEXT DEFAULT 'acs5',    -- ACS 5-year estimates
    imported_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (variable_code, geography_code, year)
);

CREATE INDEX IF NOT EXISTS idx_census_var_year ON census_timeseries (variable_code, year DESC);

-- 4. FRED series metadata (pre-populated)
CREATE TABLE IF NOT EXISTS fred_series_metadata (
    series_id   TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,              -- 'interest_rate', 'economic', 'national'
    frequency   TEXT DEFAULT 'D',           -- D=daily, M=monthly
    description TEXT
);

-- Pre-populate FRED series metadata
INSERT INTO fred_series_metadata (series_id, name, category, frequency, description) VALUES
    ('FEDFUNDS', 'Federal Funds Effective Rate', 'interest_rate', 'M', 'Rate at which banks lend reserves overnight'),
    ('DPRIME', 'Bank Prime Loan Rate', 'interest_rate', 'M', 'Rate banks charge most creditworthy customers'),
    ('DGS1MO', '1-Month Treasury Yield', 'interest_rate', 'D', 'Market yield on 1-month Treasury'),
    ('DGS3MO', '3-Month Treasury Yield', 'interest_rate', 'D', 'Market yield on 3-month Treasury'),
    ('DGS6MO', '6-Month Treasury Yield', 'interest_rate', 'D', 'Market yield on 6-month Treasury'),
    ('DGS1', '1-Year Treasury Yield', 'interest_rate', 'D', 'Market yield on 1-year Treasury'),
    ('DGS2', '2-Year Treasury Yield', 'interest_rate', 'D', 'Market yield on 2-year Treasury'),
    ('DGS5', '5-Year Treasury Yield', 'interest_rate', 'D', 'Market yield on 5-year Treasury'),
    ('DGS7', '7-Year Treasury Yield', 'interest_rate', 'D', 'Market yield on 7-year Treasury'),
    ('DGS10', '10-Year Treasury Yield', 'interest_rate', 'D', 'Benchmark for mortgage rates'),
    ('DGS20', '20-Year Treasury Yield', 'interest_rate', 'D', 'Market yield on 20-year Treasury'),
    ('DGS30', '30-Year Treasury Yield', 'interest_rate', 'D', 'Market yield on 30-year Treasury'),
    ('SOFR', 'Secured Overnight Financing Rate', 'interest_rate', 'D', 'Broad repo rate replacing LIBOR'),
    ('MORTGAGE30US', '30-Year Fixed Rate Mortgage', 'interest_rate', 'W', 'Average 30-year mortgage rate'),
    ('PHOE004UR', 'Phoenix MSA Unemployment Rate', 'economic', 'M', 'Unemployment rate for Phoenix-Mesa-Chandler MSA'),
    ('PHOE004NA', 'Phoenix MSA Employment Level', 'economic', 'M', 'All employees in thousands, Phoenix MSA'),
    ('CPIAUCSL', 'Consumer Price Index (CPI)', 'national', 'M', 'CPI for all urban consumers')
ON CONFLICT (series_id) DO NOTHING;

-- 5. Extraction log
CREATE TABLE IF NOT EXISTS extraction_log (
    id              BIGSERIAL PRIMARY KEY,
    source          TEXT NOT NULL,          -- 'costar_msa', 'costar_submarket', 'fred', 'census'
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    status          TEXT NOT NULL DEFAULT 'running',  -- 'running', 'success', 'error'
    records_upserted INT DEFAULT 0,
    error_message   TEXT,
    details         JSONB
);

CREATE INDEX IF NOT EXISTS idx_extraction_log_source ON extraction_log (source, started_at DESC);

-- ============================================================================
-- Materialized Views for fast dashboard queries
-- ============================================================================

-- Latest CoStar value per geography/concept
CREATE MATERIALIZED VIEW IF NOT EXISTS costar_latest AS
SELECT DISTINCT ON (geography_name, concept)
    geography_name,
    geography_type,
    geography_code,
    concept,
    date,
    value,
    is_forecast
FROM costar_timeseries
WHERE value IS NOT NULL AND is_forecast = FALSE
ORDER BY geography_name, concept, date DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_costar_latest_pk ON costar_latest (geography_name, concept);

-- Latest FRED value per series
CREATE MATERIALIZED VIEW IF NOT EXISTS fred_latest AS
SELECT DISTINCT ON (series_id)
    series_id,
    date,
    value
FROM fred_timeseries
WHERE value IS NOT NULL
ORDER BY series_id, date DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_fred_latest_pk ON fred_latest (series_id);

-- ============================================================================
-- Helper function to refresh materialized views
-- ============================================================================
CREATE OR REPLACE FUNCTION refresh_market_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY costar_latest;
    REFRESH MATERIALIZED VIEW CONCURRENTLY fred_latest;
END;
$$ LANGUAGE plpgsql;
