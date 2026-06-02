CREATE TABLE IF NOT EXISTS metadata.pipeline_runs (
    run_id TEXT PRIMARY KEY,
    pipeline_name TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    triggered_by TEXT,
    parameters JSONB,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS metadata.source_files (
    run_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_file_hash TEXT NOT NULL,
    rows_loaded INTEGER,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    target_table TEXT NOT NULL,
    PRIMARY KEY (run_id, source_name, source_file_hash)
);

CREATE TABLE IF NOT EXISTS quality.data_quality_results (
    check_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    layer TEXT NOT NULL,
    table_name TEXT NOT NULL,
    check_name TEXT NOT NULL,
    dimension TEXT,
    status TEXT NOT NULL,
    severity TEXT NOT NULL,
    rows_checked INTEGER,
    rows_failed INTEGER,
    details JSONB,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bronze.raw_produccion_no_convencional (
    raw_payload JSONB,
    _run_id TEXT NOT NULL,
    _source_name TEXT NOT NULL,
    _source_url TEXT NOT NULL,
    _source_file_hash TEXT NOT NULL,
    _ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    _raw_row_number BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS bronze.raw_pozos_operadoras (
    raw_payload JSONB,
    _run_id TEXT NOT NULL,
    _source_name TEXT NOT NULL,
    _source_url TEXT NOT NULL,
    _source_file_hash TEXT NOT NULL,
    _ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    _raw_row_number BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS silver.produccion_no_convencional (
    source_row JSONB,
    _run_id TEXT NOT NULL,
    _source_name TEXT NOT NULL,
    _source_url TEXT NOT NULL,
    _source_file_hash TEXT NOT NULL,
    _ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS silver.pozos_operadoras (
    source_row JSONB,
    _run_id TEXT NOT NULL,
    _source_name TEXT NOT NULL,
    _source_url TEXT NOT NULL,
    _source_file_hash TEXT NOT NULL,
    _ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gold.fact_produccion_pozo (
    sk_fact TEXT,
    _run_id TEXT,
    _source_name TEXT,
    _source_url TEXT,
    _source_file_hash TEXT,
    _ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gold.dim_pozo (
    sk_pozo TEXT PRIMARY KEY,
    _run_id TEXT,
    _source_name TEXT,
    _source_url TEXT,
    _source_file_hash TEXT,
    _ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gold.dim_fecha (
    sk_fecha TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS gold.dim_operadora (
    sk_operadora TEXT PRIMARY KEY,
    _run_id TEXT,
    _source_name TEXT,
    _source_url TEXT,
    _source_file_hash TEXT,
    _ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gold.dim_area (
    sk_area TEXT PRIMARY KEY,
    _run_id TEXT,
    _source_name TEXT,
    _source_url TEXT,
    _source_file_hash TEXT,
    _ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gold.dim_yacimiento (
    sk_yacimiento TEXT PRIMARY KEY,
    _run_id TEXT,
    _source_name TEXT,
    _source_url TEXT,
    _source_file_hash TEXT,
    _ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE OR REPLACE VIEW semantic.vw_produccion_mensual AS
SELECT 1::INTEGER AS placeholder
WHERE FALSE;

CREATE OR REPLACE VIEW semantic.vw_produccion_por_operadora AS
SELECT 1::INTEGER AS placeholder
WHERE FALSE;

CREATE OR REPLACE VIEW semantic.vw_frescura_datos AS
SELECT 1::INTEGER AS placeholder
WHERE FALSE;
