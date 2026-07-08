"""Lookup de features para serving de forecast."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import os
from typing import Any

import psycopg

FEATURE_TABLE = "features.pozo_monthly_features"
TARGET_COLUMN = "prod_pet"
FEATURE_COLUMNS = [
    "prod_pet_lag_1",
    "prod_pet_lag_2",
    "prod_pet_lag_3",
    "prod_pet_roll_mean_3",
    "prod_pet_roll_std_3",
    "mes",
    "anio",
    "antiguedad_meses",
    "cuenca",
    "provincia",
    "clasificacion",
    "tipo_reservorio",
]
METADATA_COLUMNS = ["feature_run_id", "as_of_date"]
REQUIRED_COLUMNS = ["id_pozo", "periodo_mes", *FEATURE_COLUMNS]


class FeatureLookupError(Exception):
    """Error base del lookup de features."""


class InvalidFeatureRangeError(FeatureLookupError):
    """El rango solicitado no es válido."""


class FeatureTableUnavailableError(FeatureLookupError):
    """La tabla de features no está disponible."""


class FeatureSchemaError(FeatureLookupError):
    """La tabla de features no cumple el contrato esperado."""


class PozoFeaturesNotFoundError(FeatureLookupError):
    """No hay features para el pozo solicitado."""


class FeatureRangeNotFoundError(FeatureLookupError):
    """No hay features para el rango solicitado."""


@dataclass(frozen=True)
class ForecastFeatureRow:
    id_pozo: str
    periodo_mes: date
    features: dict[str, Any]
    metadata: dict[str, Any]

    def as_model_input(self) -> dict[str, Any]:
        return {column: self.features.get(column) for column in FEATURE_COLUMNS}


def build_conninfo() -> str:
    """Construye conninfo Postgres con los mismos defaults del stack local."""
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    dbname = os.getenv("POSTGRES_DB", "warehouse")
    user = os.getenv("POSTGRES_USER", "dwh")
    password = os.getenv("POSTGRES_PASSWORD", "dwh")
    timeout = os.getenv("POSTGRES_CONNECT_TIMEOUT", "3")
    return (
        f"host={host} port={port} dbname={dbname} user={user} "
        f"password={password} connect_timeout={timeout}"
    )


def connect() -> psycopg.Connection:
    return psycopg.connect(build_conninfo())


def month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def iter_months(date_start: date, date_end: date) -> list[date]:
    if date_start > date_end:
        raise InvalidFeatureRangeError(
            "La fecha de inicio no puede ser posterior a la fecha de fin"
        )

    current = month_start(date_start)
    end = month_start(date_end)
    months = []
    while current <= end:
        months.append(current)
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return months


def _translate_db_error(exc: Exception) -> FeatureLookupError:
    if isinstance(exc, psycopg.errors.UndefinedTable):
        return FeatureTableUnavailableError(f"No existe la tabla {FEATURE_TABLE}")
    if isinstance(exc, psycopg.errors.UndefinedColumn):
        return FeatureSchemaError(
            f"La tabla {FEATURE_TABLE} no cumple el contrato de columnas esperado"
        )
    if isinstance(exc, psycopg.OperationalError):
        return FeatureTableUnavailableError(f"No se pudo conectar a Postgres: {exc}")
    return FeatureLookupError(f"No se pudieron leer features desde Postgres: {exc}")


def _column_name(description_item) -> str:
    return getattr(description_item, "name", description_item[0])


def _fetch_rows(conn: psycopg.Connection, query: str, params: tuple[Any, ...]) -> list[dict]:
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            columns = [_column_name(desc) for desc in cursor.description]
            return [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]
    except FeatureLookupError:
        raise
    except Exception as exc:
        raise _translate_db_error(exc) from exc


def _coerce_date(value: Any, column: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    raise FeatureSchemaError(f"Columna {column} no tiene formato de fecha válido")


def _coerce_scalar(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    return value


def _normalize_row(row: dict[str, Any]) -> ForecastFeatureRow:
    missing = [column for column in REQUIRED_COLUMNS if column not in row]
    if missing:
        raise FeatureSchemaError(f"Faltan columnas en {FEATURE_TABLE}: {missing}")

    metadata = {
        column: _coerce_scalar(row[column])
        for column in METADATA_COLUMNS
        if column in row
    }
    if "as_of_date" in metadata:
        metadata["as_of_date"] = _coerce_date(metadata["as_of_date"], "as_of_date")

    return ForecastFeatureRow(
        id_pozo=str(row["id_pozo"]),
        periodo_mes=month_start(_coerce_date(row["periodo_mes"], "periodo_mes")),
        features={column: _coerce_scalar(row.get(column)) for column in FEATURE_COLUMNS},
        metadata=metadata,
    )


def _pozo_exists(conn: psycopg.Connection, id_pozo: str) -> bool:
    rows = _fetch_rows(
        conn,
        f"""
        SELECT 1 AS exists
        FROM {FEATURE_TABLE}
        WHERE id_pozo = %s
        LIMIT 1
        """,
        (id_pozo,),
    )
    return bool(rows)


def get_features_for_forecast(
    id_pozo: str,
    date_start: date,
    date_end: date,
    *,
    connection: psycopg.Connection | None = None,
) -> list[ForecastFeatureRow]:
    """Lee features mensuales para un pozo y rango del contrato de forecast."""
    clean_id_pozo = id_pozo.strip()
    if not clean_id_pozo:
        raise PozoFeaturesNotFoundError("El id_pozo no puede estar vacío")

    expected_months = iter_months(date_start, date_end)
    params = (clean_id_pozo, expected_months[0], expected_months[-1])
    query = f"""
        SELECT
            id_pozo,
            periodo_mes,
            {", ".join(FEATURE_COLUMNS)},
            {", ".join(METADATA_COLUMNS)}
        FROM {FEATURE_TABLE}
        WHERE id_pozo = %s
          AND periodo_mes >= %s
          AND periodo_mes <= %s
        ORDER BY periodo_mes
    """

    should_close = connection is None
    try:
        conn = connection or connect()
    except FeatureLookupError:
        raise
    except Exception as exc:
        raise _translate_db_error(exc) from exc

    try:
        rows = [_normalize_row(row) for row in _fetch_rows(conn, query, params)]
        if not rows:
            if _pozo_exists(conn, clean_id_pozo):
                raise FeatureRangeNotFoundError(
                    f"No hay features para {clean_id_pozo} en el rango solicitado"
                )
            raise PozoFeaturesNotFoundError(
                f"No existe el pozo {clean_id_pozo} en {FEATURE_TABLE}"
            )

        available_months = {row.periodo_mes for row in rows}
        missing_months = [month for month in expected_months if month not in available_months]
        if missing_months:
            missing_text = ", ".join(month.isoformat() for month in missing_months)
            raise FeatureRangeNotFoundError(
                f"Faltan features para {clean_id_pozo} en: {missing_text}"
            )

        return rows
    finally:
        if should_close:
            conn.close()
