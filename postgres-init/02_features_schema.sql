CREATE SCHEMA IF NOT EXISTS features;

-- Feature store offline: una fila por pozo y mes.
-- Contrato (docs/contracts.md): para el mes M toda feature usa
-- solo datos hasta M-1. prod_pet es el target real del mes, nunca feature.
CREATE TABLE IF NOT EXISTS features.pozo_monthly_features (
    id_pozo TEXT NOT NULL,
    periodo_mes DATE NOT NULL,
    prod_pet NUMERIC,
    prod_pet_lag_1 NUMERIC,
    prod_pet_lag_2 NUMERIC,
    prod_pet_lag_3 NUMERIC,
    prod_pet_roll_mean_3 NUMERIC,
    prod_pet_roll_std_3 NUMERIC,
    mes SMALLINT NOT NULL,
    anio SMALLINT NOT NULL,
    antiguedad_meses INTEGER,
    cuenca TEXT,
    provincia TEXT,
    clasificacion TEXT,
    tipo_reservorio TEXT,
    feature_run_id TEXT NOT NULL,
    as_of_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id_pozo, periodo_mes)
);

CREATE INDEX IF NOT EXISTS idx_pozo_monthly_features_periodo
    ON features.pozo_monthly_features (periodo_mes);

-- Auditoría de cada corrida de generación de features.
CREATE TABLE IF NOT EXISTS features.feature_generation_runs (
    run_id TEXT PRIMARY KEY,
    as_of_date DATE NOT NULL,
    source_table TEXT NOT NULL,
    rows_written INTEGER,
    pozos INTEGER,
    periodo_min DATE,
    periodo_max DATE,
    status TEXT NOT NULL,
    error_message TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ
);

-- Estadísticas de referencia de las features del set de entrenamiento.
-- Se generan en el mismo run de training (training_run_id) y son la base
-- del drift check del Integrante 3.
CREATE TABLE IF NOT EXISTS features.feature_reference_stats (
    training_run_id TEXT NOT NULL,
    feature_name TEXT NOT NULL,
    stat_count BIGINT,
    mean NUMERIC,
    std NUMERIC,
    min NUMERIC,
    p25 NUMERIC,
    p50 NUMERIC,
    p75 NUMERIC,
    max NUMERIC,
    null_ratio NUMERIC,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (training_run_id, feature_name)
);
