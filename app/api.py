from datetime import datetime, timedelta
import os

from fastapi import FastAPI, HTTPException, Query, Security, status
from fastapi.security.api_key import APIKeyHeader
from prometheus_fastapi_instrumentator import Instrumentator, metrics


app = FastAPI(
    title="Oil & Gas Forecast API",
    description="API mock para predicción de producción",
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


def calculate_mock_production(well: dict, current_dt: datetime, start_dt: datetime) -> float:
    """
    Calcula una producción mock determinística.

    Parámetros:
      - well: Datos mock del pozo.
      - current_dt: Fecha del punto de forecast.
      - start_dt: Fecha inicial del rango.

    Returns:
      - Producción diaria esperada.
    """
    days_from_start = (current_dt - start_dt).days
    production = well["base_prod"] - (days_from_start * well["daily_decline"])
    return round(max(production, 0.0), 2)


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


@app.get("/api/v1/forecast")
def obtener_pronostico(
    id_well: str = Query(..., description="Identificador del pozo"),
    date_start: str = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),
    date_end: str = Query(..., description="Fecha de fin (YYYY-MM-DD)"),
    api_key: str = Security(get_api_key),
):
    """
    Obtiene el pronóstico de producción diaria de un pozo entre dos fechas.
    """
    if id_well not in MOCK_WELLS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe el pozo {id_well}",
        )

    start_dt = parse_date(date_start, "date_start")
    end_dt = parse_date(date_end, "date_end")

    if start_dt > end_dt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha de inicio no puede ser posterior a la fecha de fin",
        )

    well = MOCK_WELLS[id_well]
    forecast_data = []
    current_dt = start_dt

    while current_dt <= end_dt:
        forecast_data.append(
            {
                "date": current_dt.strftime("%Y-%m-%d"),
                "prod": calculate_mock_production(well, current_dt, start_dt),
            }
        )
        current_dt += timedelta(days=1)

    return {
        "id_well": id_well,
        "data": forecast_data,
    }


@app.get("/api/v1/debug/fail", include_in_schema=False)
def forzar_error_500(api_key: str = Security(get_api_key)):
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Error forzado para testing de alertas",
    )
