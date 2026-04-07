from fastapi import FastAPI, Query, Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(
    title="Oil & Gas Forecast API",
    description="API mock para predicción de producción",
    version="1.0.0"
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

API_KEY_NAME = "X-API-Key"
API_KEY_VALUE = "abcdef12345"

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY_VALUE:
        return api_key
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No se pudo validar la API Key"
    )

@app.get("/")
def ruta_principal():
    return {"mensaje": "Hola equipo! El servidor de FastAPI está funcionando perfecto."}

@app.get("/api/v1/wells")
def obtener_pozos(
    date_query: str = Query(..., description="Fecha para la cual se hace la consulta (YYYY-MM-DD)"),
    api_key: str = Security(get_api_key)
):

    return [
        {"id_well": "POZO-001"},
        {"id_well": "POZO-002"},
        {"id_well": "POZO-003"}
    ]

@app.get("/api/v1/forecast")
def obtener_pronostico(
    id_well: str = Query(..., description="Identificador del pozo"),
    date_start: str = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),
    date_end: str = Query(..., description="Fecha de fin (YYYY-MM-DD)"),
    api_key: str = Security(get_api_key)
):
    """
    Obtiene el pronóstico de producción de un pozo en un rango de fechas.
    """

    return {
        "id_well": id_well,
        "data": [
            {"date": date_start, "prod": 150.5},
            {"date": date_end, "prod": 149.8}
        ]
    }