"""Tests del drift check minimo (comparacion pura, sin DB)."""

from datetime import date

import pandas as pd

from ml.drift_check import _recent_window, compare_feature


def test_compare_feature_sin_drift_z_score_bajo():
    reference_row = pd.Series({"mean": 100.0, "std": 10.0})
    current_values = pd.Series([101.0, 99.0, 100.0])

    result = compare_feature("prod_pet_lag_1", current_values, reference_row)

    assert result["z_score"] is not None
    assert abs(result["z_score"]) < 3.0
    assert result["current_count"] == 3


def test_compare_feature_con_drift_z_score_alto():
    reference_row = pd.Series({"mean": 100.0, "std": 5.0})
    current_values = pd.Series([200.0, 205.0, 195.0])

    result = compare_feature("prod_pet_lag_1", current_values, reference_row)

    assert result["z_score"] is not None
    assert abs(result["z_score"]) > 3.0


def test_compare_feature_sin_datos_actuales_no_calcula_z_score():
    reference_row = pd.Series({"mean": 100.0, "std": 5.0})
    current_values = pd.Series([], dtype=float)

    result = compare_feature("prod_pet_lag_1", current_values, reference_row)

    assert result["z_score"] is None
    assert result["current_count"] == 0


def test_compare_feature_std_cero_no_calcula_z_score():
    reference_row = pd.Series({"mean": 100.0, "std": 0.0})
    current_values = pd.Series([100.0, 100.0])

    result = compare_feature("prod_pet_lag_1", current_values, reference_row)

    assert result["z_score"] is None


def test_recent_window_filtra_solo_los_ultimos_n_meses():
    frame = pd.DataFrame(
        {
            "periodo_mes": [
                date(2026, month, 1) for month in range(1, 7)
            ],
            "valor": range(6),
        }
    )

    recent = _recent_window(frame, window_months=2)

    assert sorted(recent["valor"].tolist()) == [4, 5]


def test_recent_window_con_menos_historia_que_la_ventana_devuelve_todo():
    frame = pd.DataFrame(
        {
            "periodo_mes": [date(2026, 1, 1), date(2026, 2, 1)],
            "valor": [0, 1],
        }
    )

    recent = _recent_window(frame, window_months=6)

    assert len(recent) == 2
