"""Acceso a las tablas del feature store en Postgres.

Toda la lectura/escritura de features.* pasa por acá para que training
(Integrante 1) y la API (Integrante 2) compartan el mismo contrato.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date

import pandas as pd
import psycopg

from ml.config import (
    FEATURE_RUNS_TABLE,
    FEATURE_TABLE,
    REFERENCE_STATS_TABLE,
    build_conninfo,
)

FEATURE_TABLE_COLUMNS = [
    "id_pozo",
    "periodo_mes",
    "prod_pet",
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
    "feature_run_id",
    "as_of_date",
]

REFERENCE_STATS_COLUMNS = [
    "training_run_id",
    "feature_name",
    "stat_count",
    "mean",
    "std",
    "min",
    "p25",
    "p50",
    "p75",
    "max",
    "null_ratio",
]


def connect() -> psycopg.Connection:
    return psycopg.connect(build_conninfo())


def _fetch_frame(conn: psycopg.Connection, query: str, params: tuple = ()) -> pd.DataFrame:
    with conn.cursor() as cursor:
        cursor.execute(query, params)
        columns = [desc.name for desc in cursor.description]
        rows = cursor.fetchall()
    return pd.DataFrame(rows, columns=columns)


def read_source_frames(
    conn: psycopg.Connection, as_of_date: date
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Lee producción mensual y atributos de pozo desde Gold hasta as_of_date."""
    produccion = _fetch_frame(
        conn,
        """
        SELECT
            idpozo AS id_pozo,
            fecha_mes::date AS periodo_mes,
            SUM(prod_pet) AS prod_pet
        FROM gold.fact_produccion_pozo
        WHERE idpozo IS NOT NULL
          AND fecha_mes IS NOT NULL
          AND fecha_mes::date <= %s
        GROUP BY idpozo, fecha_mes::date
        """,
        (as_of_date,),
    )
    pozos = _fetch_frame(
        conn,
        """
        SELECT
            idpozo AS id_pozo,
            cuenca,
            provincia,
            clasificacion,
            tipo_reservorio
        FROM gold.dim_pozo
        WHERE idpozo IS NOT NULL
        """,
    )
    return produccion, pozos


def replace_features(conn: psycopg.Connection, frame: pd.DataFrame) -> int:
    """Reemplaza el contenido del feature store con el frame recibido (COPY)."""
    missing = [column for column in FEATURE_TABLE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Faltan columnas para {FEATURE_TABLE}: {missing}")

    ordered = frame[FEATURE_TABLE_COLUMNS]
    records = ordered.astype(object).where(pd.notnull(ordered), None)

    columns_sql = ", ".join(FEATURE_TABLE_COLUMNS)
    with conn.cursor() as cursor:
        cursor.execute(f"TRUNCATE TABLE {FEATURE_TABLE}")
        with cursor.copy(
            f"COPY {FEATURE_TABLE} ({columns_sql}) FROM STDIN"
        ) as copy:
            for row in records.itertuples(index=False, name=None):
                copy.write_row(row)
    return len(records)


def read_feature_frame(
    conn: psycopg.Connection, as_of_date: date | None = None
) -> pd.DataFrame:
    """Lee el dataset de features; opcionalmente cortado a as_of_date."""
    query = f"SELECT * FROM {FEATURE_TABLE}"
    params: tuple = ()
    if as_of_date is not None:
        query += " WHERE periodo_mes <= %s"
        params = (as_of_date,)
    query += " ORDER BY id_pozo, periodo_mes"
    frame = _fetch_frame(conn, query, params)
    if not frame.empty:
        frame["periodo_mes"] = pd.to_datetime(frame["periodo_mes"])
        numeric_columns = [
            "prod_pet",
            "prod_pet_lag_1",
            "prod_pet_lag_2",
            "prod_pet_lag_3",
            "prod_pet_roll_mean_3",
            "prod_pet_roll_std_3",
            "mes",
            "anio",
            "antiguedad_meses",
        ]
        for column in numeric_columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def read_latest_features_for_pozo(
    conn: psycopg.Connection, id_pozo: str
) -> dict | None:
    """Última fila de features de un pozo (la usa la API para inferencia)."""
    frame = _fetch_frame(
        conn,
        f"""
        SELECT * FROM {FEATURE_TABLE}
        WHERE id_pozo = %s
        ORDER BY periodo_mes DESC
        LIMIT 1
        """,
        (id_pozo,),
    )
    if frame.empty:
        return None
    return frame.iloc[0].to_dict()


def record_feature_run_start(
    conn: psycopg.Connection, run_id: str, as_of_date: date, source_table: str
) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            INSERT INTO {FEATURE_RUNS_TABLE}
                (run_id, as_of_date, source_table, status)
            VALUES (%s, %s, %s, 'running')
            """,
            (run_id, as_of_date, source_table),
        )


def record_feature_run_end(
    conn: psycopg.Connection,
    run_id: str,
    *,
    status: str,
    rows_written: int | None = None,
    pozos: int | None = None,
    periodo_min: date | None = None,
    periodo_max: date | None = None,
    error_message: str | None = None,
) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            UPDATE {FEATURE_RUNS_TABLE}
            SET status = %s,
                rows_written = %s,
                pozos = %s,
                periodo_min = %s,
                periodo_max = %s,
                error_message = %s,
                finished_at = NOW()
            WHERE run_id = %s
            """,
            (status, rows_written, pozos, periodo_min, periodo_max, error_message, run_id),
        )


def read_reference_stats(
    conn: psycopg.Connection, training_run_id: str
) -> pd.DataFrame:
    """Lee las reference stats generadas en un run de training (drift check)."""
    return _fetch_frame(
        conn,
        f"SELECT * FROM {REFERENCE_STATS_TABLE} WHERE training_run_id = %s",
        (training_run_id,),
    )


def write_reference_stats(
    conn: psycopg.Connection, rows: Iterable[Mapping[str, object]]
) -> int:
    """Inserta las reference stats de un run de training (idempotente por run)."""
    rows = list(rows)
    if not rows:
        return 0
    columns_sql = ", ".join(REFERENCE_STATS_COLUMNS)
    placeholders = ", ".join(["%s"] * len(REFERENCE_STATS_COLUMNS))
    with conn.cursor() as cursor:
        cursor.execute(
            f"DELETE FROM {REFERENCE_STATS_TABLE} WHERE training_run_id = %s",
            (rows[0]["training_run_id"],),
        )
        cursor.executemany(
            f"INSERT INTO {REFERENCE_STATS_TABLE} ({columns_sql}) VALUES ({placeholders})",
            [tuple(row.get(column) for column in REFERENCE_STATS_COLUMNS) for row in rows],
        )
    return len(rows)
