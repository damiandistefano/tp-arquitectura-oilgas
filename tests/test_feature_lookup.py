from datetime import date
from decimal import Decimal

import pytest

from app import feature_lookup


class DummyConnection:
    closed = False

    def close(self):
        self.closed = True


def _feature_row(id_pozo: str, periodo_mes: date) -> dict:
    return {
        "id_pozo": id_pozo,
        "periodo_mes": periodo_mes,
        "prod_pet_lag_1": Decimal("120.5"),
        "prod_pet_lag_2": Decimal("118.0"),
        "prod_pet_lag_3": Decimal("116.0"),
        "prod_pet_roll_mean_3": Decimal("118.16"),
        "prod_pet_roll_std_3": Decimal("2.25"),
        "mes": periodo_mes.month,
        "anio": periodo_mes.year,
        "antiguedad_meses": 42,
        "cuenca": "NEUQUINA",
        "provincia": "NEUQUEN",
        "clasificacion": "EXPLOTACION",
        "tipo_reservorio": "SHALE",
        "feature_run_id": "features_run_1",
        "as_of_date": "2026-06-01",
    }


def test_get_features_for_forecast_devuelve_filas_mensuales(monkeypatch):
    conn = DummyConnection()

    def fake_fetch_rows(connection, query, params):
        assert connection is conn
        assert params == ("POZO-001", date(2026, 7, 1), date(2026, 8, 1))
        assert "features.pozo_monthly_features" in query
        return [
            _feature_row("POZO-001", date(2026, 7, 1)),
            _feature_row("POZO-001", date(2026, 8, 1)),
        ]

    monkeypatch.setattr(feature_lookup, "_fetch_rows", fake_fetch_rows)

    rows = feature_lookup.get_features_for_forecast(
        "POZO-001",
        date(2026, 7, 15),
        date(2026, 8, 20),
        connection=conn,
    )

    assert [row.periodo_mes for row in rows] == [date(2026, 7, 1), date(2026, 8, 1)]
    assert rows[0].features["prod_pet_lag_1"] == 120.5
    assert rows[0].metadata["as_of_date"] == date(2026, 6, 1)
    assert rows[0].as_model_input()["cuenca"] == "NEUQUINA"
    assert conn.closed is False


def test_get_features_for_forecast_cierra_conexion_propia(monkeypatch):
    conn = DummyConnection()

    monkeypatch.setattr(feature_lookup, "connect", lambda: conn)
    monkeypatch.setattr(
        feature_lookup,
        "_fetch_rows",
        lambda connection, query, params: [_feature_row("POZO-001", date(2026, 7, 1))],
    )

    feature_lookup.get_features_for_forecast(
        "POZO-001",
        date(2026, 7, 1),
        date(2026, 7, 31),
    )

    assert conn.closed is True


def test_get_features_for_forecast_valida_rango():
    with pytest.raises(feature_lookup.InvalidFeatureRangeError):
        feature_lookup.get_features_for_forecast(
            "POZO-001",
            date(2026, 8, 1),
            date(2026, 7, 1),
            connection=DummyConnection(),
        )


def test_get_features_for_forecast_pozo_inexistente(monkeypatch):
    calls = []

    def fake_fetch_rows(connection, query, params):
        calls.append(query)
        return []

    monkeypatch.setattr(feature_lookup, "_fetch_rows", fake_fetch_rows)

    with pytest.raises(feature_lookup.PozoFeaturesNotFoundError) as excinfo:
        feature_lookup.get_features_for_forecast(
            "POZO-999",
            date(2026, 7, 1),
            date(2026, 7, 31),
            connection=DummyConnection(),
        )

    assert "POZO-999" in str(excinfo.value)
    assert len(calls) == 2


def test_get_features_for_forecast_rango_sin_features(monkeypatch):
    def fake_fetch_rows(connection, query, params):
        if "SELECT 1 AS exists" in query:
            return [{"exists": 1}]
        return []

    monkeypatch.setattr(feature_lookup, "_fetch_rows", fake_fetch_rows)

    with pytest.raises(feature_lookup.FeatureRangeNotFoundError):
        feature_lookup.get_features_for_forecast(
            "POZO-001",
            date(2026, 7, 1),
            date(2026, 7, 31),
            connection=DummyConnection(),
        )


def test_get_features_for_forecast_detecta_meses_faltantes(monkeypatch):
    monkeypatch.setattr(
        feature_lookup,
        "_fetch_rows",
        lambda connection, query, params: [_feature_row("POZO-001", date(2026, 7, 1))],
    )

    with pytest.raises(feature_lookup.FeatureRangeNotFoundError) as excinfo:
        feature_lookup.get_features_for_forecast(
            "POZO-001",
            date(2026, 7, 1),
            date(2026, 8, 1),
            connection=DummyConnection(),
        )

    assert "2026-08-01" in str(excinfo.value)


def test_get_features_for_forecast_detecta_columnas_faltantes(monkeypatch):
    row = _feature_row("POZO-001", date(2026, 7, 1))
    row.pop("prod_pet_lag_1")
    monkeypatch.setattr(
        feature_lookup,
        "_fetch_rows",
        lambda connection, query, params: [row],
    )

    with pytest.raises(feature_lookup.FeatureSchemaError) as excinfo:
        feature_lookup.get_features_for_forecast(
            "POZO-001",
            date(2026, 7, 1),
            date(2026, 7, 31),
            connection=DummyConnection(),
        )

    assert "prod_pet_lag_1" in str(excinfo.value)


def test_get_features_for_forecast_tabla_no_disponible(monkeypatch):
    def fake_connect():
        raise feature_lookup.FeatureTableUnavailableError("tabla no disponible")

    monkeypatch.setattr(feature_lookup, "connect", fake_connect)

    with pytest.raises(feature_lookup.FeatureTableUnavailableError):
        feature_lookup.get_features_for_forecast(
            "POZO-001",
            date(2026, 7, 1),
            date(2026, 7, 31),
        )
