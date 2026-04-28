from fastapi.testclient import TestClient

from app.api import app


client = TestClient(app)

API_KEY = "abcdef12345"
HEADERS = {"X-API-Key": API_KEY}


def test_acceso_denegado_sin_api_key():
    """Prueba que si no mandamos la clave, devuelva error 403."""
    response = client.get("/api/v1/wells?date_query=2026-03-15")

    assert response.status_code == 403
    assert response.json() == {"detail": "No se pudo validar la API Key"}


def test_acceso_denegado_api_key_incorrecta():
    """Prueba que si mandamos una clave errónea, devuelva error 403."""
    headers = {"X-API-Key": "clave-falsa-123"}
    response = client.get("/api/v1/wells?date_query=2026-03-15", headers=headers)

    assert response.status_code == 403
    assert response.json() == {"detail": "No se pudo validar la API Key"}


def test_wells_requiere_date_query():
    """Prueba que el endpoint de pozos requiere el parámetro date_query."""
    response = client.get("/api/v1/wells", headers=HEADERS)

    assert response.status_code == 422


def test_wells_valida_formato_date_query():
    """Prueba que date_query debe respetar el formato YYYY-MM-DD."""
    response = client.get("/api/v1/wells?date_query=15-03-2026", headers=HEADERS)

    assert response.status_code == 400
    assert "Formato de fecha inválido" in response.json()["detail"]


def test_wells_devuelve_pozos_activos():
    """Prueba que si mandamos la clave correcta, devuelva 200 y la lista de pozos activos."""
    response = client.get("/api/v1/wells?date_query=2026-03-15", headers=HEADERS)

    assert response.status_code == 200

    wells = response.json()
    assert isinstance(wells, list)
    assert len(wells) >= 1
    assert {"id_well": "POZO-001", "name": "Pozo Norte 1"} in wells


def test_forecast_devuelve_estructura_esperada():
    """Prueba que forecast devuelva id_well y un array diario con date/prod."""
    response = client.get(
        "/api/v1/forecast?id_well=POZO-001&date_start=2026-03-15&date_end=2026-03-17",
        headers=HEADERS,
    )

    assert response.status_code == 200

    body = response.json()
    assert body["id_well"] == "POZO-001"
    assert "data" in body
    assert len(body["data"]) == 3
    assert body["data"][0] == {"date": "2026-03-15", "prod": 180.0}
    assert body["data"][1] == {"date": "2026-03-16", "prod": 179.85}
    assert body["data"][2] == {"date": "2026-03-17", "prod": 179.7}


def test_forecast_es_deterministico():
    """Prueba que dos consultas iguales devuelvan el mismo resultado."""
    url = "/api/v1/forecast?id_well=POZO-002&date_start=2026-03-15&date_end=2026-03-20"

    first_response = client.get(url, headers=HEADERS)
    second_response = client.get(url, headers=HEADERS)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == second_response.json()


def test_forecast_fechas_invalidas():
    """Prueba que el endpoint de forecast valide el formato de fechas."""
    response = client.get(
        "/api/v1/forecast?id_well=POZO-001&date_start=15-03-2026&date_end=20-03-2026",
        headers=HEADERS,
    )

    assert response.status_code == 400
    assert "Formato de fecha inválido" in response.json()["detail"]


def test_forecast_rango_invalido():
    """Prueba que la fecha de inicio no pueda ser mayor a la de fin."""
    response = client.get(
        "/api/v1/forecast?id_well=POZO-001&date_start=2026-03-20&date_end=2026-03-15",
        headers=HEADERS,
    )

    assert response.status_code == 400
    assert "no puede ser posterior" in response.json()["detail"]


def test_forecast_pozo_inexistente():
    """Prueba que consultar un pozo inexistente devuelva 404."""
    response = client.get(
        "/api/v1/forecast?id_well=POZO-999&date_start=2026-03-15&date_end=2026-03-20",
        headers=HEADERS,
    )

    assert response.status_code == 404
    assert "No existe el pozo POZO-999" in response.json()["detail"]


def test_metrics_endpoint_disponible():
    """Prueba que el endpoint /metrics de Prometheus esté disponible."""
    response = client.get("/metrics")

    assert response.status_code == 200


def test_metrics_contiene_datos_http():
    """Prueba que /metrics exponga métricas de requests HTTP."""
    client.get("/")
    response = client.get("/metrics")

    assert "http_requests_total" in response.text
