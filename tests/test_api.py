from datetime import date

from fastapi.testclient import TestClient

import app.api as api_module
from app.feature_lookup import PozoFeaturesNotFoundError
from app.model_registry import ModelUnavailableError


client = TestClient(api_module.app)

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


def test_forecast_requiere_api_key():
    """Prueba que forecast mantiene protección por API key."""
    response = client.get(
        "/api/v1/forecast?id_pozo=POZO-001&date_start=2026-07-01&date_end=2026-08-01"
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "No se pudo validar la API Key"}


def test_forecast_devuelve_estructura_esperada(monkeypatch):
    """Prueba que forecast devuelva el contrato mensual con id_pozo."""

    def fake_forecast_service(id_pozo: str, date_start: date, date_end: date):
        assert id_pozo == "POZO-001"
        assert date_start == date(2026, 7, 1)
        assert date_end == date(2026, 8, 1)
        return {
            "id_pozo": id_pozo,
            "target": "prod_pet",
            "horizon": ["2026-07", "2026-08"],
            "predictions": [
                {"periodo_mes": "2026-07", "prediction": 123.4},
                {"periodo_mes": "2026-08", "prediction": 120.1},
            ],
            "model": {
                "name": "oilgas_forecaster",
                "version": "test-version",
                "alias": "champion",
                "run_id": "test-run",
                "source": "mlflow",
            },
        }

    monkeypatch.setattr(api_module, "forecast_service", fake_forecast_service)
    response = client.get(
        "/api/v1/forecast?id_pozo=POZO-001&date_start=2026-07-01&date_end=2026-08-01",
        headers=HEADERS,
    )

    assert response.status_code == 200

    body = response.json()
    assert body == {
        "id_pozo": "POZO-001",
        "target": "prod_pet",
        "horizon": ["2026-07", "2026-08"],
        "predictions": [
            {"periodo_mes": "2026-07", "prediction": 123.4},
            {"periodo_mes": "2026-08", "prediction": 120.1},
        ],
        "model": {
            "name": "oilgas_forecaster",
            "version": "test-version",
            "alias": "champion",
            "run_id": "test-run",
            "source": "mlflow",
        },
    }
    assert "id_well" not in body


def test_forecast_no_acepta_id_well_legacy():
    """Prueba que el contrato nuevo requiere id_pozo."""
    response = client.get(
        "/api/v1/forecast?id_well=POZO-001&date_start=2026-07-01&date_end=2026-08-01",
        headers=HEADERS,
    )

    assert response.status_code == 422


def test_forecast_es_deterministico(monkeypatch):
    """Prueba que dos consultas iguales devuelvan el mismo resultado."""
    expected_body = {
        "id_pozo": "POZO-002",
        "target": "prod_pet",
        "horizon": ["2026-07"],
        "predictions": [{"periodo_mes": "2026-07", "prediction": 145.0}],
        "model": {
            "name": "oilgas_forecaster",
            "version": "test-version",
            "alias": "champion",
            "run_id": "test-run",
            "source": "local_fallback",
        },
    }

    def fake_forecast_service(id_pozo: str, date_start: date, date_end: date):
        return expected_body | {"id_pozo": id_pozo}

    monkeypatch.setattr(api_module, "forecast_service", fake_forecast_service)
    url = "/api/v1/forecast?id_pozo=POZO-002&date_start=2026-07-01&date_end=2026-07-01"

    first_response = client.get(url, headers=HEADERS)
    second_response = client.get(url, headers=HEADERS)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == second_response.json()


def test_forecast_fechas_invalidas():
    """Prueba que el endpoint de forecast valide el formato de fechas."""
    response = client.get(
        "/api/v1/forecast?id_pozo=POZO-001&date_start=15-03-2026&date_end=20-03-2026",
        headers=HEADERS,
    )

    assert response.status_code == 400
    assert "Formato de fecha inválido" in response.json()["detail"]


def test_forecast_rango_invalido():
    """Prueba que la fecha de inicio no pueda ser mayor a la de fin."""
    response = client.get(
        "/api/v1/forecast?id_pozo=POZO-001&date_start=2026-03-20&date_end=2026-03-15",
        headers=HEADERS,
    )

    assert response.status_code == 400
    assert "no puede ser posterior" in response.json()["detail"]


def test_forecast_pozo_inexistente(monkeypatch):
    """Prueba que consultar un pozo inexistente devuelva 404."""

    def fake_forecast_service(id_pozo: str, date_start: date, date_end: date):
        raise PozoFeaturesNotFoundError(f"No existe el pozo {id_pozo}")

    monkeypatch.setattr(api_module, "forecast_service", fake_forecast_service)
    response = client.get(
        "/api/v1/forecast?id_pozo=POZO-999&date_start=2026-03-15&date_end=2026-03-20",
        headers=HEADERS,
    )

    assert response.status_code == 404
    assert "No existe el pozo POZO-999" in response.json()["detail"]


def test_forecast_modelo_no_disponible(monkeypatch):
    """Prueba que la falta de modelo activo se exponga como 503."""

    def fake_forecast_service(id_pozo: str, date_start: date, date_end: date):
        raise ModelUnavailableError("No hay modelo activo")

    monkeypatch.setattr(api_module, "forecast_service", fake_forecast_service)
    response = client.get(
        "/api/v1/forecast?id_pozo=POZO-001&date_start=2026-03-15&date_end=2026-03-20",
        headers=HEADERS,
    )

    assert response.status_code == 503
    assert "No hay modelo activo" in response.json()["detail"]


def test_forecast_error_inesperado(monkeypatch):
    """Prueba que errores inesperados no expongan stack traces."""

    def fake_forecast_service(id_pozo: str, date_start: date, date_end: date):
        raise RuntimeError("fallo interno sensible")

    monkeypatch.setattr(api_module, "forecast_service", fake_forecast_service)
    response = client.get(
        "/api/v1/forecast?id_pozo=POZO-001&date_start=2026-03-15&date_end=2026-03-20",
        headers=HEADERS,
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Error inesperado al generar el forecast"}


def test_metrics_endpoint_disponible():
    """Prueba que el endpoint /metrics de Prometheus esté disponible."""
    response = client.get("/metrics")

    assert response.status_code == 200


def test_metrics_contiene_datos_http():
    """Prueba que /metrics exponga métricas de requests HTTP."""
    client.get("/")
    response = client.get("/metrics")

    assert "http_requests_total" in response.text
