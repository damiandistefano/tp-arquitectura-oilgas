"""Tests del drift check minimo (comparacion pura, sin DB)."""

from datetime import date

import pandas as pd

from ml.drift_check import _recent_window, compare_feature, run_drift_check


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


def test_run_drift_check_marca_drifted_por_feature(monkeypatch):
    from feature_store import repository
    from ml import drift_check, model_store

    class DummyConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

    reference = pd.DataFrame(
        [
            {"feature_name": "prod_pet_lag_1", "mean": 100.0, "std": 10.0},
            {"feature_name": "prod_pet_lag_2", "mean": 80.0, "std": 10.0},
        ]
    )
    features = pd.DataFrame(
        {
            "periodo_mes": [
                date(2025, 11, 1),
                date(2025, 12, 1),
                date(2026, 1, 1),
            ],
            "prod_pet_lag_1": [150.0, 155.0, 160.0],
            "prod_pet_lag_2": [78.0, 80.0, 82.0],
        }
    )

    monkeypatch.setattr(
        model_store,
        "read_champion_pointer",
        lambda: {"run_id": "champion-run"},
    )
    monkeypatch.setattr(repository, "connect", lambda: DummyConnection())
    monkeypatch.setattr(repository, "read_reference_stats", lambda _conn, _run_id: reference)
    monkeypatch.setattr(repository, "read_feature_frame", lambda _conn, _as_of_date: features)
    monkeypatch.setattr(drift_check, "NUMERIC_FEATURES", ["prod_pet_lag_1", "prod_pet_lag_2"])

    result = run_drift_check(date(2026, 1, 1), window_months=3, z_threshold=3.0)

    checks = {check["feature"]: check for check in result["checks"]}
    assert result["status"] == "drift_detected"
    assert result["drifted_features"] == ["prod_pet_lag_1"]
    assert checks["prod_pet_lag_1"]["drifted"] is True
    assert checks["prod_pet_lag_2"]["drifted"] is False
