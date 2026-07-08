CREATE SCHEMA IF NOT EXISTS metadata;

CREATE TABLE IF NOT EXISTS metadata.prediction_logs (
    prediction_id TEXT PRIMARY KEY,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    id_pozo TEXT NOT NULL,
    date_start DATE NOT NULL,
    date_end DATE NOT NULL,
    target TEXT NOT NULL,
    model_name TEXT,
    model_version TEXT,
    model_alias TEXT,
    mlflow_run_id TEXT,
    model_source TEXT,
    prediction_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL CHECK (status IN ('success', 'error')),
    error_message TEXT,
    latency_ms INTEGER NOT NULL,
    request_payload JSONB NOT NULL,
    response_summary JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_prediction_logs_requested_at
    ON metadata.prediction_logs (requested_at DESC);

CREATE INDEX IF NOT EXISTS idx_prediction_logs_id_pozo
    ON metadata.prediction_logs (id_pozo, requested_at DESC);
