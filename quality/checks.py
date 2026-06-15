"""Checks de calidad para las capas Silver, Gold y Semantic."""

from __future__ import annotations

from datetime import UTC, datetime
import sys
from uuid import uuid4

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

from extract.postgres import build_conninfo
from quality.persist_results import QualityResult, create_results_table, persist_results

CRITICAL = "CRITICAL"
WARNING = "WARNING"

EXPECTED_COLUMNS = {
    "silver.produccion_no_convencional": [
        "produccion_id",
        "idpozo",
        "anio",
        "mes",
        "fecha_mes",
        "prod_pet",
        "prod_gas",
        "prod_agua",
        "_run_id",
        "_source_file_hash",
    ],
    "gold.fact_produccion_pozo": [
        "produccion_id",
        "pozo_id",
        "fecha_mes",
        "operadora_id",
        "prod_pet",
        "prod_gas",
        "prod_agua",
        "_run_id",
        "_source_file_hash",
    ],
    "semantic.vw_produccion_mensual": [
        "fecha_mes",
        "periodo",
        "registros_produccion",
        "prod_pet_total",
        "prod_gas_total",
        "prod_agua_total",
    ],
}


def status_from_failed_rows(rows_failed: int, severity: str) -> str:
    """
    Define el estado de un check según filas fallidas y severidad.

    Parámetros:
        - rows_failed: Cantidad de filas fallidas.
        - severity: Severidad del check.

    Returns:
        PASS, WARNING o FAILED.
    """
    if rows_failed == 0:
        return "PASS"

    if severity == CRITICAL:
        return "FAILED"

    return "WARNING"


def build_result(
    *,
    run_id: str,
    layer: str,
    table_name: str,
    check_name: str,
    dimension: str,
    severity: str,
    rows_checked: int,
    rows_failed: int,
    details: dict,
) -> QualityResult:
    """
    Construye un resultado de calidad.

    Parámetros:
        - run_id: Corrida asociada.
        - layer: Capa evaluada.
        - table_name: Tabla evaluada.
        - check_name: Nombre del check.
        - dimension: Tipo de validación.
        - severity: Severidad del check.
        - rows_checked: Filas o elementos revisados.
        - rows_failed: Filas o elementos fallidos.
        - details: Detalle del resultado.

    Returns:
        Resultado de calidad listo para persistir.
    """
    return QualityResult(
        check_id=str(uuid4()),
        run_id=run_id,
        layer=layer,
        table_name=table_name,
        check_name=check_name,
        dimension=dimension,
        status=status_from_failed_rows(rows_failed, severity),
        severity=severity,
        rows_checked=rows_checked,
        rows_failed=rows_failed,
        details=details,
        executed_at=datetime.now(UTC),
    )


def fetch_scalar(conn: Connection, query: str) -> int:
    """
    Ejecuta una query que devuelve un único valor numérico.

    Parámetros:
        - conn: Conexión activa a Postgres.
        - query: SQL a ejecutar.

    Returns:
        Valor numérico obtenido.
    """
    with conn.cursor() as cursor:
        cursor.execute(query)
        row = cursor.fetchone()

    if row is None:
        return 0

    return int(next(iter(row.values())))


def get_latest_run_id(conn: Connection) -> str:
    """
    Obtiene el run_id más reciente de metadata.pipeline_runs.

    Parámetros:
        - conn: Conexión activa a Postgres.

    Returns:
        Run id más reciente o 'manual' si no existe metadata.
    """
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT run_id::text AS run_id
            FROM metadata.pipeline_runs
            ORDER BY started_at DESC
            LIMIT 1
            """
        )
        row = cursor.fetchone()

    if row is None:
        return "manual"

    return row["run_id"]


def schema_check(conn: Connection, run_id: str, table_name: str) -> QualityResult:
    """
    Valida que una tabla tenga las columnas esperadas.

    Parámetros:
        - conn: Conexión activa a Postgres.
        - run_id: Corrida asociada.
        - table_name: Tabla a validar.

    Returns:
        Resultado del check de schema.
    """
    schema, table = table_name.split(".")
    expected = EXPECTED_COLUMNS[table_name]

    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = %s
            """,
            (schema, table),
        )
        existing = {row["column_name"] for row in cursor.fetchall()}

    missing = sorted(set(expected) - existing)

    return build_result(
        run_id=run_id,
        layer=schema,
        table_name=table_name,
        check_name="expected_columns_exist",
        dimension="schema",
        severity=CRITICAL,
        rows_checked=len(expected),
        rows_failed=len(missing),
        details={"missing_columns": missing},
    )


def count_check(
    conn: Connection,
    *,
    run_id: str,
    layer: str,
    table_name: str,
    check_name: str,
    dimension: str,
    severity: str,
    rows_checked_query: str,
    rows_failed_query: str,
    details: dict,
) -> QualityResult:
    """
    Ejecuta un check basado en conteos.

    Parámetros:
        - conn: Conexión activa a Postgres.
        - run_id: Corrida asociada.
        - layer: Capa evaluada.
        - table_name: Tabla evaluada.
        - check_name: Nombre del check.
        - dimension: Tipo de validación.
        - severity: Severidad del check.
        - rows_checked_query: Query para contar filas revisadas.
        - rows_failed_query: Query para contar filas fallidas.
        - details: Detalle adicional.

    Returns:
        Resultado del check.
    """
    rows_checked = fetch_scalar(conn, rows_checked_query)
    rows_failed = fetch_scalar(conn, rows_failed_query)

    return build_result(
        run_id=run_id,
        layer=layer,
        table_name=table_name,
        check_name=check_name,
        dimension=dimension,
        severity=severity,
        rows_checked=rows_checked,
        rows_failed=rows_failed,
        details=details,
    )


def run_checks(conn: Connection, run_id: str) -> list[QualityResult]:
    """
    Ejecuta checks de calidad principales.

    Parámetros:
        - conn: Conexión activa a Postgres.
        - run_id: Corrida asociada.

    Returns:
        Lista de resultados de calidad.
    """
    results = []

    for table_name in EXPECTED_COLUMNS:
        results.append(schema_check(conn, run_id, table_name))

    results.extend(
        [
            count_check(
                conn,
                run_id=run_id,
                layer="gold",
                table_name="gold.fact_produccion_pozo",
                check_name="critical_fields_not_null",
                dimension="completeness",
                severity=CRITICAL,
                rows_checked_query="SELECT count(*) AS value FROM gold.fact_produccion_pozo",
                rows_failed_query="""
                    SELECT count(*) AS value
                    FROM gold.fact_produccion_pozo
                    WHERE produccion_id IS NULL
                       OR pozo_id IS NULL
                       OR fecha_mes IS NULL
                       OR operadora_id IS NULL
                """,
                details={"fields": ["produccion_id", "pozo_id", "fecha_mes", "operadora_id"]},
            ),
            count_check(
                conn,
                run_id=run_id,
                layer="gold",
                table_name="gold.fact_produccion_pozo",
                check_name="produccion_id_unique",
                dimension="uniqueness",
                severity=CRITICAL,
                rows_checked_query="SELECT count(*) AS value FROM gold.fact_produccion_pozo",
                rows_failed_query="""
                    SELECT count(*) - count(DISTINCT produccion_id) AS value
                    FROM gold.fact_produccion_pozo
                """,
                details={"key": "produccion_id"},
            ),
            count_check(
                conn,
                run_id=run_id,
                layer="gold",
                table_name="gold.fact_produccion_pozo",
                check_name="lineage_metadata_not_null",
                dimension="lineage",
                severity=CRITICAL,
                rows_checked_query="SELECT count(*) AS value FROM gold.fact_produccion_pozo",
                rows_failed_query="""
                    SELECT count(*) AS value
                    FROM gold.fact_produccion_pozo
                    WHERE _run_id IS NULL
                       OR _source_file_hash IS NULL
                """,
                details={"fields": ["_run_id", "_source_file_hash"]},
            ),
            count_check(
                conn,
                run_id=run_id,
                layer="gold",
                table_name="gold.fact_produccion_pozo",
                check_name="fact_has_matching_dimensions",
                dimension="lineage",
                severity=CRITICAL,
                rows_checked_query="SELECT count(*) AS value FROM gold.fact_produccion_pozo",
                rows_failed_query="""
                    SELECT count(*) AS value
                    FROM gold.fact_produccion_pozo f
                    LEFT JOIN gold.dim_pozo p ON f.pozo_id = p.pozo_id
                    LEFT JOIN gold.dim_fecha d ON f.fecha_mes = d.fecha_mes
                    LEFT JOIN gold.dim_operadora o ON f.operadora_id = o.operadora_id
                    WHERE p.pozo_id IS NULL
                       OR d.fecha_mes IS NULL
                       OR o.operadora_id IS NULL
                """,
                details={"dimensions": ["dim_pozo", "dim_fecha", "dim_operadora"]},
            ),
            count_check(
                conn,
                run_id=run_id,
                layer="semantic",
                table_name="semantic.vw_frescura_datos",
                check_name="latest_period_not_too_old",
                dimension="freshness",
                severity=WARNING,
                rows_checked_query="SELECT 1 AS value",
                rows_failed_query="""
                    SELECT CASE
                        WHEN current_date - max(fecha_mes)::date > 120 THEN 1
                        ELSE 0
                    END AS value
                    FROM gold.fact_produccion_pozo
                """,
                details={"max_days_since_latest_period": 120},
            ),
        ]
    )

    return results


def main() -> int:
    """Ejecuta checks, persiste resultados y falla si hay errores críticos."""
    with psycopg.connect(build_conninfo(), row_factory=dict_row) as conn:
        create_results_table(conn)
        run_id = get_latest_run_id(conn)
        results = run_checks(conn, run_id)
        persist_results(conn, results)
        conn.commit()

    for result in results:
        print(
            f"{result.status} | {result.severity} | "
            f"{result.table_name} | {result.check_name} | "
            f"failed={result.rows_failed}"
        )

    failed_critical = [
        result
        for result in results
        if result.severity == CRITICAL and result.status == "FAILED"
    ]

    if failed_critical:
        print(f"Quality gate failed: {len(failed_critical)} critical check(s) failed.")
        return 1

    print("Quality gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
