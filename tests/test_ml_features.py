"""Tests del contrato de features: lags calendario y no-leakage temporal."""

from datetime import date

import pandas as pd
import pytest

from ml.build_features import build_feature_frame

RUN_ID = "features_test_run"


def _produccion(rows):
    return pd.DataFrame(rows, columns=["id_pozo", "periodo_mes", "prod_pet"])


def _pozos(ids):
    return pd.DataFrame(
        {
            "id_pozo": ids,
            "cuenca": "NEUQUINA",
            "provincia": "NEUQUEN",
            "clasificacion": "EXPLOTACION",
            "tipo_reservorio": "SHALE",
        }
    )


@pytest.fixture
def frame_continuo():
    rows = [
        ("P1", date(2025, month, 1), month * 10.0) for month in range(1, 9)
    ]
    return build_feature_frame(
        _produccion(rows), _pozos(["P1"]), date(2025, 8, 1), RUN_ID
    )


def test_lags_son_meses_calendario_anteriores(frame_continuo):
    fila_mayo = frame_continuo[frame_continuo["periodo_mes"] == date(2025, 5, 1)].iloc[0]
    assert fila_mayo["prod_pet"] == 50.0
    assert fila_mayo["prod_pet_lag_1"] == 40.0
    assert fila_mayo["prod_pet_lag_2"] == 30.0
    assert fila_mayo["prod_pet_lag_3"] == 20.0


def test_rolling_excluye_el_mes_actual(frame_continuo):
    # Ventana M-3..M-1 para mayo: feb, mar, abr -> (20+30+40)/3
    fila_mayo = frame_continuo[frame_continuo["periodo_mes"] == date(2025, 5, 1)].iloc[0]
    assert fila_mayo["prod_pet_roll_mean_3"] == pytest.approx(30.0)
    # Si incluyera al mes actual daría (30+40+50)/3 = 40
    assert fila_mayo["prod_pet_roll_mean_3"] != pytest.approx(40.0)


def test_primer_mes_no_tiene_lags(frame_continuo):
    fila_enero = frame_continuo[frame_continuo["periodo_mes"] == date(2025, 1, 1)].iloc[0]
    assert pd.isna(fila_enero["prod_pet_lag_1"])
    assert pd.isna(fila_enero["prod_pet_lag_2"])
    assert pd.isna(fila_enero["prod_pet_lag_3"])


def test_mes_faltante_no_corre_la_ventana():
    # P2 no reporta marzo: el lag_1 de abril es marzo (NaN), no febrero
    rows = [
        ("P2", date(2025, 1, 1), 10.0),
        ("P2", date(2025, 2, 1), 20.0),
        ("P2", date(2025, 4, 1), 40.0),
    ]
    frame = build_feature_frame(_produccion(rows), _pozos(["P2"]), date(2025, 12, 1), RUN_ID)

    fila_abril = frame[frame["periodo_mes"] == date(2025, 4, 1)].iloc[0]
    assert pd.isna(fila_abril["prod_pet_lag_1"])
    assert fila_abril["prod_pet_lag_2"] == 20.0
    # No se inventan filas para meses sin dato en la fuente
    assert date(2025, 3, 1) not in set(frame["periodo_mes"])


def test_as_of_date_corta_los_datos():
    rows = [("P1", date(2025, month, 1), month * 10.0) for month in range(1, 9)]
    frame = build_feature_frame(_produccion(rows), _pozos(["P1"]), date(2025, 5, 1), RUN_ID)
    assert frame["periodo_mes"].max() == date(2025, 5, 1)


def test_antiguedad_y_calendario():
    rows = [("P1", date(2025, month, 1), month * 10.0) for month in range(1, 9)]
    frame = build_feature_frame(_produccion(rows), _pozos(["P1"]), date(2025, 8, 1), RUN_ID)
    fila_agosto = frame[frame["periodo_mes"] == date(2025, 8, 1)].iloc[0]
    assert fila_agosto["antiguedad_meses"] == 7
    assert fila_agosto["mes"] == 8
    assert fila_agosto["anio"] == 2025


def test_categoricas_y_metadata_del_run(frame_continuo):
    assert set(frame_continuo["cuenca"]) == {"NEUQUINA"}
    assert set(frame_continuo["feature_run_id"]) == {RUN_ID}
    assert set(frame_continuo["as_of_date"]) == {date(2025, 8, 1)}
