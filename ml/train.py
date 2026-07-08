"""Entrenamiento del modelo de forecast de prod_pet.

Pasos (contrato en docs/contracts.md):
1. Lee el feature store cortado a --as-of-date.
2. Split temporal: últimos 6 meses a test (o 3 si la historia no alcanza).
3. Entrena el modelo y evalúa contra el baseline prod_pet_lag_1 en el
   mismo set de test.
4. Guarda artefactos locales (fallback de sandbox) y, si MLFLOW_TRACKING_URI
   está seteado, loguea el run y registra el modelo en MLflow.
5. Calcula feature_reference_stats del set de entrenamiento en el MISMO run.

Uso:
    python -m ml.train --as-of-date 2026-06-01
"""

from __future__ import annotations

import argparse
from datetime import date
import json
import logging
import sys
import uuid

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from ml import model_store
from ml.baseline import evaluate_baseline
from ml.config import (
    BASELINE_FEATURE,
    CATEGORICAL_FEATURES,
    FALLBACK_TEST_MONTHS,
    FEATURE_COLUMNS,
    MIN_TRAIN_MONTHS,
    MODEL_NAME,
    NUMERIC_FEATURES,
    PRIMARY_METRIC,
    TARGET_COLUMN,
    TEST_MONTHS,
    get_mlflow_tracking_uri,
)
from ml.metrics import regression_metrics
from ml.reference_stats import compute_reference_stats

logger = logging.getLogger(__name__)

RANDOM_STATE = 42


def temporal_split(
    frame: pd.DataFrame,
    test_months: int = TEST_MONTHS,
    fallback_test_months: int = FALLBACK_TEST_MONTHS,
    min_train_months: int = MIN_TRAIN_MONTHS,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Split temporal reproducible: los últimos N meses calendario van a test.

    Nunca hay solapamiento de meses entre train y test, y test siempre es
    posterior a train (evita métricas irreales de un split random).
    """
    months = pd.to_datetime(pd.Series(frame["periodo_mes"].unique())).sort_values()
    total_months = len(months)

    if total_months >= test_months + min_train_months:
        holdout = test_months
    elif total_months >= fallback_test_months + min_train_months:
        holdout = fallback_test_months
    else:
        raise ValueError(
            f"Historia insuficiente para split temporal: hay {total_months} meses "
            f"y se necesitan al menos {fallback_test_months + min_train_months}"
        )

    split_start = months.iloc[-holdout]
    periodo = pd.to_datetime(frame["periodo_mes"])
    train = frame[periodo < split_start]
    test = frame[periodo >= split_start]

    split_info = {
        "test_months": holdout,
        "test_start": str(split_start.date()),
        "train_months": total_months - holdout,
        "periodo_min": str(months.iloc[0].date()),
        "periodo_max": str(months.iloc[-1].date()),
    }
    return train, test, split_info


def make_pipeline() -> Pipeline:
    """HistGradientBoosting tolera NaN en numéricas (lags de pozos nuevos)."""
    preprocess = ColumnTransformer(
        transformers=[
            (
                "categoricas",
                Pipeline(
                    [
                        (
                            "imputer",
                            SimpleImputer(strategy="constant", fill_value="desconocido"),
                        ),
                        (
                            "onehot",
                            OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                        ),
                    ]
                ),
                CATEGORICAL_FEATURES,
            ),
            ("numericas", "passthrough", NUMERIC_FEATURES),
        ]
    )
    model = HistGradientBoostingRegressor(random_state=RANDOM_STATE)
    return Pipeline([("preprocess", preprocess), ("model", model)])


def evaluate_on_test(model, test_frame: pd.DataFrame) -> dict[str, float]:
    """Evalúa sobre filas donde el baseline también está definido (comparación justa)."""
    evaluable = test_frame.dropna(subset=[TARGET_COLUMN, BASELINE_FEATURE])
    if evaluable.empty:
        raise ValueError("El set de test no tiene filas evaluables")
    predictions = model.predict(evaluable[FEATURE_COLUMNS])
    return regression_metrics(evaluable[TARGET_COLUMN], predictions)


def _log_to_mlflow(run_id: str, model, run_info: dict, train_frame: pd.DataFrame):
    """Tracking en MLflow si está configurado; el pipeline nunca depende de él."""
    tracking_uri = get_mlflow_tracking_uri()
    if not tracking_uri:
        logger.info("MLFLOW_TRACKING_URI no seteado: solo artefactos locales")
        return None
    try:
        import mlflow  # noqa: PLC0415

        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(MODEL_NAME)
        with mlflow.start_run(run_name=run_id) as active_run:
            mlflow.log_params(
                {
                    "as_of_date": run_info["as_of_date"],
                    "feature_run_id": run_info["feature_run_id"],
                    "model_type": "HistGradientBoostingRegressor",
                    "random_state": RANDOM_STATE,
                    "features": ",".join(FEATURE_COLUMNS),
                    **{f"split_{k}": v for k, v in run_info["split"].items()},
                }
            )
            for name, value in run_info["metrics"]["model"].items():
                mlflow.log_metric(f"model_{name}", value)
            for name, value in run_info["metrics"]["baseline"].items():
                mlflow.log_metric(f"baseline_{name}", value)
            logged = mlflow.sklearn.log_model(
                model,
                artifact_path="model",
                registered_model_name=MODEL_NAME,
                input_example=train_frame[FEATURE_COLUMNS].head(5),
            )
            info = {
                "tracking_uri": tracking_uri,
                "mlflow_run_id": active_run.info.run_id,
                "model_version": getattr(logged, "registered_model_version", None),
            }
            logger.info("Run logueado en MLflow: %s", info)
            return info
    except Exception as exc:  # noqa: BLE001
        logger.warning("MLflow no disponible (%s): sigo solo con artefactos locales", exc)
        return None


def run_training(as_of_date: date) -> dict:
    from feature_store import repository

    run_id = f"model_{as_of_date:%Y%m%d}_{uuid.uuid4().hex[:8]}"

    with repository.connect() as conn:
        features = repository.read_feature_frame(conn, as_of_date)
        if features.empty:
            raise RuntimeError(
                "El feature store está vacío: correr primero "
                f"`python -m ml.build_features --as-of-date {as_of_date}`"
            )

        trainable = features.dropna(subset=[TARGET_COLUMN])
        train_frame, test_frame, split_info = temporal_split(trainable)

        pipeline = make_pipeline()
        pipeline.fit(train_frame[FEATURE_COLUMNS], train_frame[TARGET_COLUMN])

        model_metrics = evaluate_on_test(pipeline, test_frame)
        baseline_metrics = evaluate_baseline(test_frame)

        run_info = {
            "run_id": run_id,
            "model_name": MODEL_NAME,
            "as_of_date": str(as_of_date),
            "feature_run_id": str(features["feature_run_id"].iloc[0]),
            "split": split_info,
            "n_train": int(len(train_frame)),
            "n_test": int(len(test_frame)),
            "primary_metric": PRIMARY_METRIC,
            "metrics": {"model": model_metrics, "baseline": baseline_metrics},
            "feature_columns": FEATURE_COLUMNS,
        }

        mlflow_info = _log_to_mlflow(run_id, pipeline, run_info, train_frame)
        if mlflow_info:
            run_info["mlflow"] = mlflow_info

        model_store.save_run_artifacts(run_id, pipeline, run_info)

        # Reference stats en el MISMO run: si hay candidato, hay referencia
        stats_rows = compute_reference_stats(train_frame, run_id)
        repository.write_reference_stats(conn, stats_rows)
        run_info["reference_stats_rows"] = len(stats_rows)

    return run_info


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Entrena el modelo de prod_pet")
    parser.add_argument(
        "--as-of-date",
        type=date.fromisoformat,
        default=date.today(),
        help="Corte temporal (YYYY-MM-DD)",
    )
    args = parser.parse_args(argv)

    run_info = run_training(args.as_of_date)
    print(json.dumps(run_info, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
