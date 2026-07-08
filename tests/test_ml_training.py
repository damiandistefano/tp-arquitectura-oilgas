"""Tests del split temporal, baseline y pipeline de entrenamiento."""

import numpy as np
import pandas as pd
import pytest

from ml.baseline import evaluate_baseline
from ml.train import evaluate_on_test, make_pipeline, temporal_split


def _feature_frame(n_months: int, n_pozos: int = 3) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    months = pd.date_range("2024-01-01", periods=n_months, freq="MS")
    rows = []
    for pozo in range(n_pozos):
        base = 100.0 * (pozo + 1)
        for index, month in enumerate(months):
            prod = base + index * 5 + rng.normal(0, 1)
            rows.append(
                {
                    "id_pozo": f"P{pozo}",
                    "periodo_mes": month,
                    "prod_pet": prod,
                    "prod_pet_lag_1": prod - 5,
                    "prod_pet_lag_2": prod - 10,
                    "prod_pet_lag_3": prod - 15,
                    "prod_pet_roll_mean_3": prod - 10,
                    "prod_pet_roll_std_3": 5.0,
                    "mes": month.month,
                    "anio": month.year,
                    "antiguedad_meses": index,
                    "cuenca": "NEUQUINA",
                    "provincia": "NEUQUEN",
                    "clasificacion": "EXPLOTACION",
                    "tipo_reservorio": "SHALE" if pozo % 2 == 0 else None,
                }
            )
    return pd.DataFrame(rows)


def test_split_usa_ultimos_6_meses_si_alcanza():
    train, test, info = temporal_split(_feature_frame(18))
    assert info["test_months"] == 6
    assert pd.to_datetime(train["periodo_mes"]).max() < pd.to_datetime(
        test["periodo_mes"]
    ).min()
    assert test["periodo_mes"].nunique() == 6


def test_split_cae_a_3_meses_con_poca_historia():
    _, test, info = temporal_split(_feature_frame(10))
    assert info["test_months"] == 3
    assert test["periodo_mes"].nunique() == 3


def test_split_falla_claro_sin_historia_suficiente():
    with pytest.raises(ValueError, match="Historia insuficiente"):
        temporal_split(_feature_frame(5))


def test_split_no_solapa_meses():
    train, test, _ = temporal_split(_feature_frame(15))
    assert set(train["periodo_mes"]).isdisjoint(set(test["periodo_mes"]))


def test_baseline_es_lag_1():
    frame = pd.DataFrame(
        {
            "prod_pet": [100.0, 110.0],
            "prod_pet_lag_1": [90.0, 100.0],
        }
    )
    metrics = evaluate_baseline(frame)
    assert metrics["mae"] == pytest.approx(10.0)


def test_baseline_ignora_filas_sin_lag():
    frame = pd.DataFrame(
        {
            "prod_pet": [100.0, 110.0],
            "prod_pet_lag_1": [None, 100.0],
        }
    )
    metrics = evaluate_baseline(frame)
    assert metrics["mae"] == pytest.approx(10.0)


def test_pipeline_entrena_y_evalua_con_nans_y_categoricas():
    frame = _feature_frame(18)
    # Pozos nuevos sin historia completa: lags NaN deben tolerarse
    frame.loc[frame.index[:4], ["prod_pet_lag_2", "prod_pet_lag_3"]] = np.nan
    train, test, _ = temporal_split(frame)

    from ml.config import FEATURE_COLUMNS, TARGET_COLUMN

    pipeline = make_pipeline()
    pipeline.fit(train[FEATURE_COLUMNS], train[TARGET_COLUMN])
    metrics = evaluate_on_test(pipeline, test)

    assert np.isfinite(metrics["mae"])
    assert np.isfinite(metrics["rmse"])
    assert np.isfinite(metrics["smape"])
