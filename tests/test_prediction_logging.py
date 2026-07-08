from datetime import date

from fastapi.testclient import TestClient
import pytest

import app.api as api_module
from app import prediction_logging
from app.model_registry import ModelUnavailableError

API_KEY = "abcdef12345"
HEADERS = {"X-API-Key": API_KEY}


class DummyCursor:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, query, params):
        self.connection.executed_query = query
        self.connection.executed_params = params


class DummyConnection:
    autocommit = False

    def __init__(self):
        self.committed = False
        self.closed = False
        self.executed_query = None
        self.executed_params = None

    def cursor(self):
        return DummyCursor(self)

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


def _record(**overrides) -> prediction_logging.PredictionLogRecord:
    base = {
        "id_pozo": "POZO-001",
        "date_start": date(2026, 7, 1),
        "date_end": date(2026, 8, 1),
        "target": "prod_pet",
        "status": "success",
        "latency_ms": 12,
        "request_payload": {"id_pozo": "POZO-001"},
        "prediction_count": 2,
        "response_summary": {"horizon": ["2026-07", "2026-08"]},
        "model_name": "oilgas_forecaster",
        "model_version": "v1",
        "model_alias": "champion",
        "mlflow_run_id": "run-1",
        "model_source": "mlflow",
    }
    return prediction_logging.PredictionLogRecord(**(base | overrides))


def _forecast_body():
    return {
        "id_pozo": "POZO-001",
        "target": "prod_pet",
        "horizon": ["2026-07"],
        "predictions": [{"periodo_mes": "2026-07", "prediction": 123.4}],
        "model": {
            "name": "oilgas_forecaster",
            "version": "v1",
            "alias": "champion",
            "run_id": "run-1",
            "source": "mlflow",
        },
    }


def test_db_values_no_guarda_api_key():
    values = prediction_logging._db_values(
        _record(
            request_payload={
                "id_pozo": "POZO-001",
                "X-API-Key": API_KEY,
                "nested": {"authorization": "Bearer secret"},
            }
        )
    )

    assert values["request_payload"]["X-API-Key"] == "[redacted]"
    assert values["request_payload"]["nested"]["authorization"] == "[redacted]"


def test_log_prediction_inserta_registro():
    conn = DummyConnection()

    prediction_logging.log_prediction(_record(), connection=conn)

    assert "metadata.prediction_logs" in conn.executed_query
    assert conn.executed_params["id_pozo"] == "POZO-001"
    assert conn.executed_params["status"] == "success"
    assert conn.committed is True
    assert conn.closed is False


def test_log_prediction_envuelve_error_controlado():
    class BrokenCursor(DummyCursor):
        def execute(self, query, params):
            raise RuntimeError("db down")

    class BrokenConnection(DummyConnection):
        def cursor(self):
            return BrokenCursor(self)

    with pytest.raises(prediction_logging.PredictionLoggingError) as excinfo:
        prediction_logging.log_prediction(_record(), connection=BrokenConnection())

    assert "db down" in str(excinfo.value)


def test_api_registra_log_en_happy_path(monkeypatch):
    records = []

    monkeypatch.setattr(api_module, "forecast_service", lambda *args: _forecast_body())
    monkeypatch.setattr(
        api_module.prediction_logging,
        "log_prediction",
        lambda record: records.append(record),
    )

    response = TestClient(api_module.app).get(
        "/api/v1/forecast?id_pozo=POZO-001&date_start=2026-07-01&date_end=2026-07-01",
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert len(records) == 1
    record = records[0]
    assert record.status == "success"
    assert record.prediction_count == 1
    assert record.model_name == "oilgas_forecaster"
    assert "X-API-Key" not in record.request_payload


def test_api_registra_log_en_error_path(monkeypatch):
    records = []

    def fake_forecast_service(*args):
        raise ModelUnavailableError("No hay modelo activo")

    monkeypatch.setattr(api_module, "forecast_service", fake_forecast_service)
    monkeypatch.setattr(
        api_module.prediction_logging,
        "log_prediction",
        lambda record: records.append(record),
    )

    response = TestClient(api_module.app).get(
        "/api/v1/forecast?id_pozo=POZO-001&date_start=2026-07-01&date_end=2026-07-01",
        headers=HEADERS,
    )

    assert response.status_code == 503
    assert len(records) == 1
    assert records[0].status == "error"
    assert records[0].error_message == "No hay modelo activo"
    assert records[0].prediction_count == 0


def test_fallo_de_logging_no_rompe_happy_path(monkeypatch):
    def fail_logging(record):
        raise prediction_logging.PredictionLoggingError("db down")

    monkeypatch.setattr(api_module, "forecast_service", lambda *args: _forecast_body())
    monkeypatch.setattr(api_module.prediction_logging, "log_prediction", fail_logging)

    response = TestClient(api_module.app).get(
        "/api/v1/forecast?id_pozo=POZO-001&date_start=2026-07-01&date_end=2026-07-01",
        headers=HEADERS,
    )

    assert response.status_code == 200
