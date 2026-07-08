"""Persistencia de metadata de inferencias en Postgres."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import logging
from typing import Any
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb

from app.feature_lookup import build_conninfo

logger = logging.getLogger(__name__)

PREDICTION_LOG_TABLE = "metadata.prediction_logs"
SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "x-api-key",
    "authorization",
    "password",
    "token",
    "secret",
}


class PredictionLoggingError(Exception):
    """No se pudo persistir el log de predicción."""


@dataclass(frozen=True)
class PredictionLogRecord:
    id_pozo: str
    date_start: date
    date_end: date
    target: str
    status: str
    latency_ms: int
    request_payload: dict[str, Any]
    prediction_count: int = 0
    response_summary: dict[str, Any] | None = None
    error_message: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    model_alias: str | None = None
    mlflow_run_id: str | None = None
    model_source: str | None = None
    prediction_id: str = field(default_factory=lambda: str(uuid4()))


def connect() -> psycopg.Connection:
    return psycopg.connect(build_conninfo())


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("_", "-")
    return normalized in SENSITIVE_KEYS


def scrub_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[redacted]" if _is_sensitive_key(str(key)) else scrub_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [scrub_sensitive(item) for item in value[:50]]
    return value


def _truncate(value: str | None, limit: int = 500) -> str | None:
    if value is None:
        return None
    return value[:limit]


def _db_values(record: PredictionLogRecord) -> dict[str, Any]:
    return {
        "prediction_id": record.prediction_id,
        "id_pozo": record.id_pozo,
        "date_start": record.date_start,
        "date_end": record.date_end,
        "target": record.target,
        "model_name": record.model_name,
        "model_version": record.model_version,
        "model_alias": record.model_alias,
        "mlflow_run_id": record.mlflow_run_id,
        "model_source": record.model_source,
        "prediction_count": record.prediction_count,
        "status": record.status,
        "error_message": _truncate(record.error_message),
        "latency_ms": record.latency_ms,
        "request_payload": scrub_sensitive(record.request_payload),
        "response_summary": scrub_sensitive(record.response_summary or {}),
    }


def log_prediction(
    record: PredictionLogRecord,
    *,
    connection: psycopg.Connection | None = None,
) -> None:
    """Inserta un registro de inferencia en metadata.prediction_logs."""
    values = _db_values(record)
    should_close = connection is None
    try:
        conn = connection or connect()
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO {PREDICTION_LOG_TABLE} (
                    prediction_id,
                    id_pozo,
                    date_start,
                    date_end,
                    target,
                    model_name,
                    model_version,
                    model_alias,
                    mlflow_run_id,
                    model_source,
                    prediction_count,
                    status,
                    error_message,
                    latency_ms,
                    request_payload,
                    response_summary
                )
                VALUES (
                    %(prediction_id)s,
                    %(id_pozo)s,
                    %(date_start)s,
                    %(date_end)s,
                    %(target)s,
                    %(model_name)s,
                    %(model_version)s,
                    %(model_alias)s,
                    %(mlflow_run_id)s,
                    %(model_source)s,
                    %(prediction_count)s,
                    %(status)s,
                    %(error_message)s,
                    %(latency_ms)s,
                    %(request_payload)s,
                    %(response_summary)s
                )
                """,
                {
                    **values,
                    "request_payload": Jsonb(values["request_payload"]),
                    "response_summary": Jsonb(values["response_summary"]),
                },
            )
        if not getattr(conn, "autocommit", False):
            conn.commit()
    except Exception as exc:
        logger.warning("No se pudo persistir prediction log: %s", exc)
        raise PredictionLoggingError(str(exc)) from exc
    finally:
        if should_close and "conn" in locals():
            conn.close()
