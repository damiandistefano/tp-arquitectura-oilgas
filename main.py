from fastapi import FastAPI

app = FastAPI(
    title="Oil & Gas Forecast API",
    description="API mock para predicción de producción",
    version="1.0.0"
)

@app.get("/")
def ruta_principal():
    return {"mensaje": "Hola equipo! El servidor de FastAPI está funcionando perfecto."}