from fastapi.testclient import TestClient
from app.api import app  

client = TestClient(app)

API_KEY = "abcdef12345"

def test_acceso_denegado_sin_api_key():
    """Prueba que si no mandamos la clave, devuelva error 403"""
    response = client.get("/api/v1/wells?date_query=2026-03-15")
    assert response.status_code == 403
    assert response.json() == {"detail": "No se pudo validar la API Key"}

def test_acceso_permitido_con_api_key():
    """Prueba que si mandamos la clave correcta, devuelva 200 y la lista de pozos"""
    headers = {"X-API-Key": API_KEY}
    response = client.get("/api/v1/wells?date_query=2026-03-15", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_acceso_denegado_api_key_incorrecta():
    """Prueba que si mandamos una clave errónea, devuelva error 403"""
    headers = {"X-API-Key": "clave-falsa-123"}
    response = client.get("/api/v1/wells?date_query=2026-03-15", headers=headers)
    assert response.status_code == 403
    assert response.json() == {"detail": "No se pudo validar la API Key"}

def test_forecast_fechas_invalidas():
    """Prueba que el endpoint de forecast valide el formato de fechas"""
    headers = {"X-API-Key": API_KEY}
    response = client.get(
        "/api/v1/forecast?id_well=POZO-001&date_start=15-03-2026&date_end=20-03-2026", 
        headers=headers
    )
    assert response.status_code == 400
    assert "Formato de fecha inválido" in response.json()["detail"]

def test_forecast_rango_invalido():
    """Prueba que la fecha de inicio no pueda ser mayor a la de fin"""
    headers = {"X-API-Key": API_KEY}
    response = client.get(
        "/api/v1/forecast?id_well=POZO-001&date_start=2026-03-20&date_end=2026-03-15", 
        headers=headers
    )
    assert response.status_code == 400
    assert "no puede ser posterior" in response.json()["detail"]


def test_metrics_endpoint_disponible():
    """Prueba que el endpoint /metrics de Prometheus este disponible"""
    response = client.get("/metrics")
    assert response.status_code == 200

def test_metrics_contiene_datos_http():
    """Prueba que /metrics exponga metricas de requests HTTP"""
    client.get("/")
    response = client.get("/metrics")
    assert "http_requests_total" in response.text