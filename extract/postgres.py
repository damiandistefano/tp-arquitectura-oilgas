"""Postgres execution helpers for ingestion loads."""

from __future__ import annotations

import os

import psycopg

from .logging_config import get_logger
from .retry import retry_with_backoff

logger = get_logger(__name__)


def build_conninfo() -> str:
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    dbname = os.getenv("POSTGRES_DB", "warehouse")
    user = os.getenv("POSTGRES_USER", "dwh")
    password = os.getenv("POSTGRES_PASSWORD", "dwh")
    return f"host={host} port={port} dbname={dbname} user={user} password={password}"


@retry_with_backoff()
def _connect_to_postgres() -> psycopg.Connection:
    """Connect to postgres with retry logic."""
    conninfo = build_conninfo()
    logger.info("Connecting to PostgreSQL...")
    conn = psycopg.connect(conninfo)
    logger.info("PostgreSQL connection established")
    return conn


def has_source_been_loaded(source_name: str, source_file_hash: str) -> bool:
    """Check if a source file has already been loaded successfully."""
    try:
        conn = _connect_to_postgres()
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM metadata.source_files WHERE source_name = %s AND source_file_hash = %s LIMIT 1",
                    (source_name, source_file_hash),
                )
                result = cursor.fetchone()
                loaded = result is not None
                logger.info(
                    f"Source {source_name} (hash: {source_file_hash}) "
                    f"{'already loaded' if loaded else 'not yet loaded'}"
                )
                return loaded
    except psycopg.Error as e:
        logger.warning(f"Could not check if source was loaded: {e}. Proceeding with load.")
        return False


def execute_statements(statements: list[str]) -> None:
    if not statements:
        logger.info("No statements to execute")
        return

    logger.info(f"Executing {len(statements)} statement(s)")
    try:
        conn = _connect_to_postgres()
        with conn:
            with conn.cursor() as cursor:
                for idx, statement in enumerate(statements, 1):
                    try:
                        logger.debug(f"Executing statement {idx}/{len(statements)}")
                        cursor.execute(statement)
                    except psycopg.Error as e:
                        logger.error(
                            f"Error executing statement {idx}/{len(statements)}: {e}"
                        )
                        raise
            logger.info(f"Successfully executed all {len(statements)} statement(s)")
    except psycopg.Error as e:
        logger.error(f"PostgreSQL error: {e}")
        raise
