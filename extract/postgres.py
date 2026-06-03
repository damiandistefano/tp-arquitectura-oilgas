"""Postgres execution helpers for ingestion loads."""

from __future__ import annotations

import os

import psycopg


def build_conninfo() -> str:
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    dbname = os.getenv("POSTGRES_DB", "warehouse")
    user = os.getenv("POSTGRES_USER", "dwh")
    password = os.getenv("POSTGRES_PASSWORD", "dwh")
    return f"host={host} port={port} dbname={dbname} user={user} password={password}"


def execute_statements(statements: list[str]) -> None:
    if not statements:
        return

    conninfo = build_conninfo()
    with psycopg.connect(conninfo) as conn:
        with conn.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
