"""Servicio de inferencia para forecasts mensuales."""

from __future__ import annotations

from datetime import date
from typing import Any

from app import feature_lookup, model_registry
from app.schemas import ForecastPrediction, ForecastResponse

TARGET = "prod_pet"


class ForecastInferenceError(Exception):
    """Error base del servicio de inferencia."""


class ModelPredictionError(ForecastInferenceError):
    """El modelo activo no pudo generar predicciones válidas."""


def _predict_with_model(model, rows: list[dict[str, Any]]):
    if not hasattr(model, "predict"):
        raise ModelPredictionError("El modelo activo no expone método predict")

    try:
        return model.predict(rows)
    except Exception as list_exc:
        try:
            import pandas as pd  # noqa: PLC0415
        except ImportError:
            raise ModelPredictionError(
                "El modelo activo no pudo predecir con filas de features"
            ) from list_exc

        try:
            return model.predict(pd.DataFrame(rows))
        except Exception as dataframe_exc:
            raise ModelPredictionError(
                "El modelo activo falló al generar predicciones"
            ) from dataframe_exc


def _as_sequence(raw_predictions) -> list[Any]:
    if hasattr(raw_predictions, "tolist"):
        raw_predictions = raw_predictions.tolist()
    if isinstance(raw_predictions, tuple):
        raw_predictions = list(raw_predictions)
    if not isinstance(raw_predictions, list):
        raw_predictions = [raw_predictions]
    return raw_predictions


def _normalize_predictions(raw_predictions, expected_count: int) -> list[float]:
    values = _as_sequence(raw_predictions)
    if len(values) != expected_count:
        raise ModelPredictionError(
            "La cantidad de predicciones no coincide con el horizonte solicitado"
        )

    try:
        return [round(float(value), 4) for value in values]
    except (TypeError, ValueError) as exc:
        raise ModelPredictionError("El modelo devolvió predicciones no numéricas") from exc


def generate_forecast(
    id_pozo: str,
    date_start: date,
    date_end: date,
    *,
    feature_lookup_func=None,
    active_model_func=None,
) -> ForecastResponse:
    """Genera forecast mensual model-backed para el contrato público."""
    lookup = feature_lookup_func or feature_lookup.get_features_for_forecast
    load_active_model = active_model_func or model_registry.get_active_model

    feature_rows = lookup(id_pozo, date_start, date_end)
    active_model = load_active_model()
    model_input = [row.as_model_input() for row in feature_rows]
    raw_predictions = _predict_with_model(active_model.model, model_input)
    predictions = _normalize_predictions(raw_predictions, len(feature_rows))

    return ForecastResponse(
        id_pozo=id_pozo,
        target=TARGET,
        horizon=[row.periodo_mes.strftime("%Y-%m") for row in feature_rows],
        predictions=[
            ForecastPrediction(
                periodo_mes=row.periodo_mes.strftime("%Y-%m"),
                prediction=prediction,
            )
            for row, prediction in zip(feature_rows, predictions, strict=True)
        ],
        model=active_model.metadata.as_dict(),
    )
