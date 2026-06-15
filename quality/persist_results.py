"""Helpers para persistir resultados de calidad en Postgres."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from psycopg import Connection
from psycopg.types.json import Jsonb


@dataclass
class QualityResult:
    """
    Representa el resultado de un check de calidad.

    Parámetros:
        - check_id: Identificador único del check ejecutado.
        - run_id: Corrida asociada.
        - layer: Capa evaluada.
        - table_name: Tabla evaluada.
        - check_name: Nombre del check.
        - dimension: Tipo de validación.
        - status: PASS, WARNING o FAILED.
        - severity: CRITICAL o WARNING.
        - rows_checked: Filas o elementos revisados.
        - rows_failed: Filas o elementos fallidos.
        - details: Detalle del resultado.
        - executed_at: Fecha de ejecución.
    """

    check_id: str
    run_id: str
    layer: str
    table_name: str
    check_name: str
    dimension: str
    status: str
    severity: str
    rows_checked: int
    rows_failed: int
    details: dict[str, Any]
    executed_at: datetime


def create_results_table(conn: Connection) -> None:
    """
    Crea la tabla de resultados de calidad si no existe.

    Parámetros:
        - conn: Conexión activa a Postgres.
    """
    with conn.cursor() as cursor:
        cursor.execute(
            """
            CREATE SCHEMA IF NOT EXISTS quality;

            CREATE TABLE IF NOT EXISTS quality.data_quality_results (
                check_id TEXT PRIMARY KEY,
                run_id TEXT,
                layer TEXT NOT NULL,
                table_name TEXT NOT NULL,
                check_name TEXT NOT NULL,
                dimension TEXT NOT NULL,
                status TEXT NOT NULL,
                severity TEXT NOT NULL,
                rows_checked BIGINT NOT NULL,
                rows_failed BIGINT NOT NULL,
                details JSONB NOT NULL,
                executed_at TIMESTAMPTZ NOT NULL
            );
            """
        )


def persist_results(conn: Connection, results: list[QualityResult]) -> None:
    """
    Inserta resultados de calidad en Postgres.

    Parámetros:
        - conn: Conexión activa a Postgres.
        - results: Lista de resultados a persistir.
    """
    if not results:
        return

    with conn.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO quality.data_quality_results (
                check_id,
                run_id,
                layer,
                table_name,
                check_name,
                dimension,
                status,
                severity,
                rows_checked,
                rows_failed,
                details,
                executed_at
            )
            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
            """,
            [
                (
                    result.check_id,
                    result.run_id,
                    result.layer,
                    result.table_name,
                    result.check_name,
                    result.dimension,
                    result.status,
                    result.severity,
                    result.rows_checked,
                    result.rows_failed,
                    Jsonb(result.details),
                    result.executed_at,
                )
                for result in results
            ],
        )
