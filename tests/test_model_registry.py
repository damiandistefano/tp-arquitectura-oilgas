import sys
from types import SimpleNamespace

import pytest

from app import model_registry


def _clear_registry_env(monkeypatch):
    for name in [
        "MLFLOW_TRACKING_URI",
        "MLFLOW_MODEL_NAME",
        "MLFLOW_MODEL_ALIAS",
        "LOCAL_MODEL_FALLBACK_PATH",
        "LOCAL_MODEL_FALLBACK_ENABLED",
        "ML_ARTIFACTS_DIR",
    ]:
        monkeypatch.delenv(name, raising=False)


def test_get_active_model_usa_mlflow_si_esta_configurado(monkeypatch):
    _clear_registry_env(monkeypatch)
    loaded_model = object()

    class FakeClient:
        def __init__(self, tracking_uri: str):
            assert tracking_uri == "http://mlflow:5000"

        def get_model_version_by_alias(self, model_name: str, alias: str):
            assert model_name == "oilgas_forecaster"
            assert alias == "champion"
            return SimpleNamespace(version="12", run_id="mlflow_run_abc")

    def fake_load_model(model_uri: str):
        assert model_uri == "models:/oilgas_forecaster@champion"
        return loaded_model

    fake_mlflow = SimpleNamespace(
        MlflowClient=FakeClient,
        pyfunc=SimpleNamespace(load_model=fake_load_model),
    )
    monkeypatch.setitem(sys.modules, "mlflow", fake_mlflow)
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
    monkeypatch.setenv("LOCAL_MODEL_FALLBACK_ENABLED", "false")

    active = model_registry.get_active_model()

    assert active.model is loaded_model
    assert active.metadata.as_dict() == {
        "name": "oilgas_forecaster",
        "version": "12",
        "alias": "champion",
        "run_id": "mlflow_run_abc",
        "source": "mlflow",
    }


def test_fallback_local_json_queda_visible(monkeypatch, tmp_path):
    _clear_registry_env(monkeypatch)
    fallback_path = tmp_path / "fallback_model.json"
    fallback_path.write_text(
        '{"version": "fallback-v1", "run_id": "fallback-run-1"}',
        encoding="utf-8",
    )
    monkeypatch.setenv("LOCAL_MODEL_FALLBACK_PATH", str(fallback_path))

    active = model_registry.get_active_model()

    assert isinstance(active.model, model_registry.LocalFallbackForecaster)
    assert active.metadata.source == "local_fallback"
    assert active.metadata.version == "fallback-v1"
    assert active.metadata.run_id == "fallback-run-1"


def test_fallback_builtin_deriva_metadata_de_runtime(monkeypatch):
    _clear_registry_env(monkeypatch)

    active = model_registry.get_active_model()

    assert isinstance(active.model, model_registry.LocalFallbackForecaster)
    assert active.metadata.source == "local_fallback"
    assert active.metadata.version.startswith("local-")
    assert active.metadata.run_id.startswith("local_fallback_")
    assert active.model.predict([{"prod_pet_lag_1": 120.555}]) == [120.56]


def test_get_active_model_falla_si_no_hay_mlflow_ni_fallback(monkeypatch):
    _clear_registry_env(monkeypatch)
    monkeypatch.setenv("LOCAL_MODEL_FALLBACK_ENABLED", "false")

    with pytest.raises(model_registry.ModelUnavailableError) as excinfo:
        model_registry.get_active_model()

    assert "No hay modelo activo disponible" in str(excinfo.value)


def test_get_active_model_rechaza_metadata_incompleta(monkeypatch):
    _clear_registry_env(monkeypatch)
    monkeypatch.setenv("LOCAL_MODEL_FALLBACK_ENABLED", "false")
    monkeypatch.setattr(
        model_registry,
        "_load_from_mlflow",
        lambda: model_registry.ActiveModel(
            model=object(),
            metadata=model_registry.ModelMetadata(
                name="oilgas_forecaster",
                version="",
                alias="champion",
                run_id="",
                source="mlflow",
            ),
        ),
    )

    with pytest.raises(model_registry.ModelUnavailableError) as excinfo:
        model_registry.get_active_model()

    assert "version/run_id" in str(excinfo.value)


def test_load_model_devuelve_solo_el_modelo(monkeypatch):
    _clear_registry_env(monkeypatch)
    fake_model = object()
    monkeypatch.setattr(
        model_registry,
        "get_active_model",
        lambda: model_registry.ActiveModel(
            model=fake_model,
            metadata=model_registry.ModelMetadata(
                name="oilgas_forecaster",
                version="v1",
                alias="champion",
                run_id="run-1",
                source="local_fallback",
            ),
        ),
    )

    assert model_registry.load_model() is fake_model
