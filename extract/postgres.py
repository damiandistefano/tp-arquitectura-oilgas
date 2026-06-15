"""Postgres helpers for ingestion loads."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import json
import os

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from .logging_config import get_logger
from .retry import retry_with_backoff

logger = get_logger(__name__)

JSONB_COLUMNS = {"raw_payload", "parameters", "details"}


def build_conninfo() -> str:
    """
    Construye el string de conexión a Postgres desde variables de entorno.

    Returns:
        String de conexión compatible con psycopg.
    """
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    dbname = os.getenv("POSTGRES_DB", "warehouse")
    user = os.getenv("POSTGRES_USER", "dwh")
    password = os.getenv("POSTGRES_PASSWORD", "dwh")
    return f"host={host} port={port} dbname={dbname} user={user} password={password}"


def get_batch_size() -> int:
    """
    Obtiene el tamaño de batch para cargas masivas.

    Returns:
        Tamaño de batch configurado. Por defecto usa 5000 filas.
    """
    raw_value = os.getenv("DATA_LOAD_BATCH_SIZE", "5000")

    try:
        batch_size = int(raw_value)
    except ValueError as exc:
        raise ValueError("DATA_LOAD_BATCH_SIZE must be an integer") from exc

    if batch_size <= 0:
        raise ValueError("DATA_LOAD_BATCH_SIZE must be greater than 0")

    return batch_size


@retry_with_backoff()
def connect_to_postgres() -> psycopg.Connection:
    """
    Abre una conexión a Postgres con retry.

    Returns:
        Conexión activa a Postgres.
    """
    conninfo = build_conninfo()
    logger.info("Connecting to PostgreSQL...")
    conn = psycopg.connect(conninfo)
    logger.info("PostgreSQL connection established")
    return conn


def _qualified_table(table_name: str) -> sql.Composed:
    parts = table_name.split(".")
    if len(parts) != 2 or not all(parts):
        raise ValueError(f"Expected table name in schema.table format, got: {table_name}")

    schema, table = parts
    return sql.SQL(".").join([sql.Identifier(schema), sql.Identifier(table)])


def _adapt_value(column: str, value):
    if column not in JSONB_COLUMNS:
        return value

    if value is None:
        return None

    if isinstance(value, Jsonb):
        return value

    if isinstance(value, (dict, list)):
        return Jsonb(value)

    if isinstance(value, str):
        return Jsonb(json.loads(value))

    return Jsonb(value)


def _chunk_rows(rows: list[Mapping[str, object]], batch_size: int):
    for start in range(0, len(rows), batch_size):
        yield rows[start : start + batch_size]


def has_source_been_loaded(source_name: str, source_file_hash: str) -> bool:
    """
    Revisa si una fuente ya fue cargada exitosamente.

    Parámetros:
        - source_name: Nombre lógico de la fuente.
        - source_file_hash: Hash del archivo descargado.

    Returns:
        True si ya existe en metadata.source_files. False en caso contrario.
    """
    try:
        conn = connect_to_postgres()
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 1
                    FROM metadata.source_files
                    WHERE source_name = %s
                      AND source_file_hash = %s
                    LIMIT 1
                    """,
                    (source_name, source_file_hash),
                )
                result = cursor.fetchone()
                loaded = result is not None
                logger.info(
                    "Source %s (hash: %s) %s",
                    source_name,
                    source_file_hash,
                    "already loaded" if loaded else "not yet loaded",
                )
                return loaded
    except psycopg.Error as exc:
        logger.warning(
            "Could not check if source was loaded: %s. Proceeding with load.",
            exc,
        )
        return False


def insert_rows(
    table_name: str,
    rows: Iterable[Mapping[str, object]],
    *,
    conn: psycopg.Connection | None = None,
    batch_size: int | None = None,
) -> int:
    """
    Inserta filas en Postgres usando batches y parámetros.

    Parámetros:
        - table_name: Tabla destino en formato schema.table.
        - rows: Filas a insertar.
        - conn: Conexión opcional. Si se pasa, reutiliza la transacción activa.
        - batch_size: Tamaño de batch. Si no se pasa, usa DATA_LOAD_BATCH_SIZE.

    Returns:
        Cantidad de filas insertadas.
    """
    rows = list(rows)
    if not rows:
        logger.info("No rows to insert into %s", table_name)
        return 0

    batch_size = batch_size or get_batch_size()
    columns = list(rows[0].keys())

    insert_query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        _qualified_table(table_name),
        sql.SQL(", ").join(sql.Identifier(column) for column in columns),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
    )

    owns_connection = conn is None
    active_conn = conn or connect_to_postgres()

    try:
        with active_conn.cursor() as cursor:
            total_batches = (len(rows) + batch_size - 1) // batch_size
            logger.info(
                "Inserting %s row(s) into %s in %s batch(es) of up to %s",
                len(rows),
                table_name,
                total_batches,
                batch_size,
            )

            for batch_number, batch in enumerate(_chunk_rows(rows, batch_size), start=1):
                values = [
                    tuple(_adapt_value(column, row.get(column)) for column in columns)
                    for row in batch
                ]

                cursor.executemany(insert_query, values)
                logger.info(
                    "Inserted batch %s/%s into %s (%s row(s))",
                    batch_number,
                    total_batches,
                    table_name,
                    len(batch),
                )

        return len(rows)
    finally:
        if owns_connection:
            active_conn.close()


def execute_statements(statements: list[str]) -> None:
    """
    Ejecuta SQL crudo.

    Se mantiene para compatibilidad con tests/código existente. Para cargas grandes
    conviene usar insert_rows(), porque evita armar INSERTs gigantes.
    """
    if not statements:
        logger.info("No statements to execute")
        return

    logger.info("Executing %s raw SQL statement(s)", len(statements))

    try:
        conn = connect_to_postgres()
        with conn:
            with conn.cursor() as cursor:
                for idx, statement in enumerate(statements, 1):
                    try:
                        logger.debug("Executing statement %s/%s", idx, len(statements))
                        cursor.execute(statement)
                    except psycopg.Error as exc:
                        logger.error(
                            "Error executing statement %s/%s: %s",
                            idx,
                            len(statements),
                            exc,
                        )
                        raise
            logger.info("Successfully executed all %s statement(s)", len(statements))
    except psycopg.Error as exc:
        logger.error("PostgreSQL error: %s", exc)
        raise