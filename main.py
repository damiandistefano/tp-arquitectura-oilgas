from fastapi import FastAPI, Query

app = FastAPI(
    title="Oil & Gas Forecast API",
    description="API mock para predicción de producción",
    version="1.0.0"
)

@app.get("/")
def ruta_principal():
    return {"mensaje": "Hola equipo! El servidor de FastAPI está funcionando perfecto."}

@app.get("/api/v1/wells")
def obtener_pozos(
    date_query: str = Query(..., description="Fecha para la cual se hace la consulta (YYYY-MM-DD)")
):

    return [
        {"id_well": "POZO-001"},
        {"id_well": "POZO-002"},
        {"id_well": "POZO-003"}
    ]