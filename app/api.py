from datetime import date, datetime
import logging
import os
import time

from fastapi import FastAPI, HTTPException, Query, Security, status
from fastapi.security.api_key import APIKeyHeader
from prometheus_fastapi_instrumentator import Instrumentator, metrics

from app.feature_lookup import (
    FeatureRangeNotFoundError,
    FeatureSchemaError,
    FeatureTableUnavailableError,
    InvalidFeatureRangeError,
    PozoFeaturesNotFoundError,
)
from app.ml_inference import ModelPredictionError, generate_forecast
from app.model_registry import ModelUnavailableError
from app import prediction_logging
from app.schemas import ForecastResponse

logger = logging.getLogger(__name__)


app = FastAPI(
    title="Oil & Gas Forecast API",
    description="API para predicción mensual de producción",
    version="1.0.0",
)

Instrumentator(excluded_handlers=["/metrics"]).add(
    metrics.requests()
).add(
    metrics.latency(
        buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0)
    )
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

API_KEY_NAME = "X-API-Key"
API_KEY_VALUE = os.getenv("API_KEY_VALUE", "abcdef12345")

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

MOCK_WELLS = {
    "POZO-001": {
        "id_well": "POZO-001",
        "name": "Pozo Norte 1",
        "active_from": "2020-01-01",
        "active_to": None,
        "base_prod": 180.0,
        "daily_decline": 0.15,
    },
    "POZO-002": {
        "id_well": "POZO-002",
        "name": "Pozo Sur 2",
        "active_from": "2021-06-01",
        "active_to": None,
        "base_prod": 145.0,
        "daily_decline": 0.10,
    },
    "POZO-003": {
        "id_well": "POZO-003",
        "name": "Pozo Oeste 3",
        "active_from": "2019-03-15",
        "active_to": "2026-12-31",
        "base_prod": 110.0,
        "daily_decline": 0.05,
    },
}


async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY_VALUE:
        return api_key

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No se pudo validar la API Key",
    )


def parse_date(date_value: str, field_name: str) -> datetime:
    """
    Convierte una fecha YYYY-MM-DD a datetime.

    Parámetros:
      - date_value: Fecha recibida como string.
      - field_name: Nombre del campo para informar errores.

    Returns:
      - Fecha convertida a datetime.
    """
    try:
        return datetime.strptime(date_value, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato de fecha inválido en {field_name}. Use YYYY-MM-DD",
        ) from exc


def is_well_active(well: dict, query_date: datetime) -> bool:
    """
    Indica si un pozo está activo para una fecha dada.

    Parámetros:
      - well: Datos mock del pozo.
      - query_date: Fecha consultada.

    Returns:
      - True si el pozo está activo, False si no.
    """
    active_from = parse_date(well["active_from"], "active_from")
    active_to = parse_date(well["active_to"], "active_to") if well["active_to"] else None

    if query_date < active_from:
        return False

    if active_to and query_date > active_to:
        return False

    return True


@app.get("/")
def ruta_principal():
    return {"mensaje": "Hola equipo! El servidor de FastAPI está funcionando perfecto."}


@app.get("/health", tags=["Monitoring"])
def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "oil-gas-forecast-api",
    }


@app.get("/api/v1/wells")
def obtener_pozos(
    date_query: str = Query(..., description="Fecha para la cual se hace la consulta (YYYY-MM-DD)"),
    api_key: str = Security(get_api_key),
):
    query_dt = parse_date(date_query, "date_query")

    return [
        {
            "id_well": well["id_well"],
            "name": well["name"],
        }
        for well in MOCK_WELLS.values()
        if is_well_active(well, query_dt)
    ]


def forecast_service(id_pozo: str, date_start: date, date_end: date) -> ForecastResponse:
    """Punto de integración para el servicio de inferencia."""
    return generate_forecast(id_pozo, date_start, date_end)


def _elapsed_ms(start_time: float) -> int:
    return int((time.perf_counter() - start_time) * 1000)


def _object_as_dict(value) -> dict:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return {}


def _response_summary(response) -> tuple[int, dict, dict]:
    response_dict = _object_as_dict(response)
    predictions = response_dict.get("predictions", [])
    model = _object_as_dict(response_dict.get("model"))
    summary = {
        "horizon": response_dict.get("horizon", []),
        "prediction_count": len(predictions),
        "model": model,
    }
    return len(predictions), model, summary


def _record_forecast_log(
    *,
    id_pozo: str,
    date_start: date,
    date_end: date,
    status_value: str,
    latency_ms: int,
    response=None,
    error_message: str | None = None,
) -> None:
    prediction_count, model, summary = _response_summary(response)
    record = prediction_logging.PredictionLogRecord(
        id_pozo=id_pozo,
        date_start=date_start,
        date_end=date_end,
        target="prod_pet",
        status=status_value,
        latency_ms=latency_ms,
        request_payload={
            "id_pozo": id_pozo,
            "date_start": date_start.isoformat(),
            "date_end": date_end.isoformat(),
        },
        prediction_count=prediction_count,
        response_summary=summary if status_value == "success" else {},
        error_message=error_message,
        model_name=model.get("name"),
        model_version=model.get("version"),
        model_alias=model.get("alias"),
        mlflow_run_id=model.get("run_id"),
        model_source=model.get("source"),
    )
    try:
        prediction_logging.log_prediction(record)
    except prediction_logging.PredictionLoggingError as exc:
        logger.warning("No se pudo registrar prediction log: %s", exc)


@app.get("/api/v1/forecast", response_model=ForecastResponse)
def obtener_pronostico(
    id_pozo: str = Query(..., description="Identificador del pozo"),
    date_start: str = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),
    date_end: str = Query(..., description="Fecha de fin (YYYY-MM-DD)"),
    api_key: str = Security(get_api_key),
):
    """
    Obtiene el pronóstico mensual de producción de un pozo entre dos fechas.
    """
    request_started = time.perf_counter()
    start_dt = parse_date(date_start, "date_start").date()
    end_dt = parse_date(date_end, "date_end").date()

    if start_dt > end_dt:
        detail = "La fecha de inicio no puede ser posterior a la fecha de fin"
        _record_forecast_log(
            id_pozo=id_pozo,
            date_start=start_dt,
            date_end=end_dt,
            status_value="error",
            latency_ms=_elapsed_ms(request_started),
            error_message=detail,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )

    try:
        response = forecast_service(id_pozo, start_dt, end_dt)
        _record_forecast_log(
            id_pozo=id_pozo,
            date_start=start_dt,
            date_end=end_dt,
            status_value="success",
            latency_ms=_elapsed_ms(request_started),
            response=response,
        )
        return response
    except HTTPException:
        raise
    except InvalidFeatureRangeError as exc:
        _record_forecast_log(
            id_pozo=id_pozo,
            date_start=start_dt,
            date_end=end_dt,
            status_value="error",
            latency_ms=_elapsed_ms(request_started),
            error_message=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except (PozoFeaturesNotFoundError, FeatureRangeNotFoundError) as exc:
        _record_forecast_log(
            id_pozo=id_pozo,
            date_start=start_dt,
            date_end=end_dt,
            status_value="error",
            latency_ms=_elapsed_ms(request_started),
            error_message=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (
        FeatureTableUnavailableError,
        FeatureSchemaError,
        ModelUnavailableError,
        ModelPredictionError,
    ) as exc:
        _record_forecast_log(
            id_pozo=id_pozo,
            date_start=start_dt,
            date_end=end_dt,
            status_value="error",
            latency_ms=_elapsed_ms(request_started),
            error_message=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        detail = "Error inesperado al generar el forecast"
        _record_forecast_log(
            id_pozo=id_pozo,
            date_start=start_dt,
            date_end=end_dt,
            status_value="error",
            latency_ms=_elapsed_ms(request_started),
            error_message=detail,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        ) from exc


@app.get("/api/v1/debug/fail", include_in_schema=False)
def forzar_error_500(api_key: str = Security(get_api_key)):
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Error forzado para testing de alertas",
    )
