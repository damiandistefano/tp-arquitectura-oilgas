"""Configuración central del pipeline de ML.

Los nombres de columnas y reglas vienen del contrato cerrado en
docs/contracts.md. Cualquier cambio se acuerda ahí primero.
"""

from __future__ import annotations

import os
from pathlib import Path

# Contrato: target y grano
TARGET_COLUMN = "prod_pet"
ID_COLUMN = "id_pozo"
PERIOD_COLUMN = "periodo_mes"

# Feature store
FEATURES_SCHEMA = "features"
FEATURE_TABLE = "features.pozo_monthly_features"
FEATURE_RUNS_TABLE = "features.feature_generation_runs"
REFERENCE_STATS_TABLE = "features.feature_reference_stats"
SOURCE_FACT_TABLE = "gold.fact_produccion_pozo"
SOURCE_DIM_POZO_TABLE = "gold.dim_pozo"

# Features mínimas del contrato
NUMERIC_FEATURES = [
    "prod_pet_lag_1",
    "prod_pet_lag_2",
    "prod_pet_lag_3",
    "prod_pet_roll_mean_3",
    "prod_pet_roll_std_3",
    "mes",
    "anio",
    "antiguedad_meses",
]
CATEGORICAL_FEATURES = [
    "cuenca",
    "provincia",
    "clasificacion",
    "tipo_reservorio",
]
FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES

# Baseline del contrato: predicción ingenua = último valor conocido
BASELINE_FEATURE = "prod_pet_lag_1"

# Split temporal: últimos 6 meses para test; si no alcanza, últimos 3
TEST_MONTHS = 6
FALLBACK_TEST_MONTHS = 3
MIN_TRAIN_MONTHS = 6

# Métrica primaria del gate de promoción (menor es mejor)
PRIMARY_METRIC = "mae"

# Registro de modelos
MODEL_NAME = "oilgas_forecaster"
CHAMPION_ALIAS = "champion"

# Drift check minimo: compara la distribucion reciente de features contra
# las feature_reference_stats del champion (calculadas en su training run).
DRIFT_WINDOW_MONTHS = 3
DRIFT_Z_THRESHOLD = 3.0


def get_artifacts_dir() -> Path:
    """Directorio local de artefactos (fallback de sandbox sin MLflow)."""
    return Path(os.getenv("ML_ARTIFACTS_DIR", "ml_artifacts"))


def get_runs_dir() -> Path:
    return get_artifacts_dir() / "runs"


def get_champion_pointer_path() -> Path:
    return get_artifacts_dir() / "champion.json"


def get_mlflow_tracking_uri() -> str | None:
    """URI de MLflow si está configurado; None deshabilita el tracking."""
    return os.getenv("MLFLOW_TRACKING_URI") or None


def build_conninfo() -> str:
    """String de conexión a Postgres desde variables de entorno.

    Mismos defaults que extract.postgres: dentro de docker el host es
    `postgres`; desde el host se usa .env con localhost:5433.
    """
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    dbname = os.getenv("POSTGRES_DB", "warehouse")
    user = os.getenv("POSTGRES_USER", "dwh")
    password = os.getenv("POSTGRES_PASSWORD", "dwh")
    return f"host={host} port={port} dbname={dbname} user={user} password={password}"
