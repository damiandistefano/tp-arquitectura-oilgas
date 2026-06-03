"""Minimal Postgres helper for Bronze loads."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import json


def _format_sql_value(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (dict, list)):
        json_text = json.dumps(value, ensure_ascii=True).replace("'", "''")
        return f"'{json_text}'::jsonb"
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def build_insert_sql(table_name: str, rows: Iterable[Mapping[str, object]]) -> str:
    rows = list(rows)
    if not rows:
        return ""

    columns = list(rows[0].keys())
    values_sql = []
    for row in rows:
        values = ", ".join(_format_sql_value(row[column]) for column in columns)
        values_sql.append(f"({values})")

    columns_sql = ", ".join(columns)
    values_joined = ",\n".join(values_sql)
    return f"INSERT INTO {table_name} ({columns_sql}) VALUES\n{values_joined};"
