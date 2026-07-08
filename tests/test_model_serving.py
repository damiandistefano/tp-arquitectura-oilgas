from datetime import date

import pytest

from app import model_registry
from app.feature_lookup import ForecastFeatureRow
from app.ml_inference import ModelPredictionError, generate_forecast


class FakeModel:
    def __init__(self, predictions):
        self.predictions = predictions

    def predict(self, rows):
        assert rows[0]["prod_pet_lag_1"] == 120.0
        return self.predictions


class ModelWithoutPredict:
    pass


def _feature_row(periodo_mes: date, lag_1: float = 120.0) -> ForecastFeatureRow:
    return ForecastFeatureRow(
        id_pozo="POZO-001",
        periodo_mes=periodo_mes,
        features={
            "prod_pet_lag_1": lag_1,
            "prod_pet_lag_2": lag_1 - 2,
            "prod_pet_lag_3": lag_1 - 4,
            "prod_pet_roll_mean_3": lag_1 - 2,
            "prod_pet_roll_std_3": 2.0,
            "mes": periodo_mes.month,
            "anio": periodo_mes.year,
            "antiguedad_meses": 30,
            "cuenca": "NEUQUINA",
            "provincia": "NEUQUEN",
            "clasificacion": "EXPLOTACION",
            "tipo_reservorio": "SHALE",
        },
        metadata={"feature_run_id": "features_run_1"},
    )


def _active_model(model, source: str = "mlflow") -> model_registry.ActiveModel:
    return model_registry.ActiveModel(
        model=model,
        metadata=model_registry.ModelMetadata(
            name="oilgas_forecaster",
            version="runtime-version",
            alias="champion",
            run_id="runtime-run",
            source=source,
        ),
    )


def test_generate_forecast_happy_path_model_backed():
    rows = [_feature_row(date(2026, 7, 1)), _feature_row(date(2026, 8, 1), 118.0)]

    response = generate_forecast(
        "POZO-001",
        date(2026, 7, 1),
        date(2026, 8, 1),
        feature_lookup_func=lambda id_pozo, date_start, date_end: rows,
        active_model_func=lambda: _active_model(FakeModel([123.45678, 120.0])),
    )

    assert response.id_pozo == "POZO-001"
    assert response.target == "prod_pet"
    assert response.horizon == ["2026-07", "2026-08"]
    assert [prediction.prediction for prediction in response.predictions] == [
        123.4568,
        120.0,
    ]
    assert response.model.source == "mlflow"
    assert response.model.version == "runtime-version"
    assert response.model.run_id == "runtime-run"


def test_generate_forecast_fallback_local_visible():
    rows = [_feature_row(date(2026, 7, 1), 130.555)]

    response = generate_forecast(
        "POZO-001",
        date(2026, 7, 1),
        date(2026, 7, 31),
        feature_lookup_func=lambda id_pozo, date_start, date_end: rows,
        active_model_func=lambda: _active_model(
            model_registry.LocalFallbackForecaster(),
            source="local_fallback",
        ),
    )

    assert response.predictions[0].prediction == 130.56
    assert response.model.source == "local_fallback"


def test_generate_forecast_rechaza_modelo_sin_predict():
    rows = [_feature_row(date(2026, 7, 1))]

    with pytest.raises(ModelPredictionError) as excinfo:
        generate_forecast(
            "POZO-001",
            date(2026, 7, 1),
            date(2026, 7, 31),
            feature_lookup_func=lambda id_pozo, date_start, date_end: rows,
            active_model_func=lambda: _active_model(ModelWithoutPredict()),
        )

    assert "predict" in str(excinfo.value)


def test_generate_forecast_rechaza_cantidad_invalida_de_predicciones():
    rows = [_feature_row(date(2026, 7, 1)), _feature_row(date(2026, 8, 1), 118.0)]

    with pytest.raises(ModelPredictionError) as excinfo:
        generate_forecast(
            "POZO-001",
            date(2026, 7, 1),
            date(2026, 8, 1),
            feature_lookup_func=lambda id_pozo, date_start, date_end: rows,
            active_model_func=lambda: _active_model(FakeModel([123.4])),
        )

    assert "cantidad de predicciones" in str(excinfo.value)


def test_generate_forecast_rechaza_predicciones_no_numericas():
    rows = [_feature_row(date(2026, 7, 1))]

    with pytest.raises(ModelPredictionError) as excinfo:
        generate_forecast(
            "POZO-001",
            date(2026, 7, 1),
            date(2026, 7, 31),
            feature_lookup_func=lambda id_pozo, date_start, date_end: rows,
            active_model_func=lambda: _active_model(FakeModel(["no-numero"])),
        )

    assert "no numéricas" in str(excinfo.value)
