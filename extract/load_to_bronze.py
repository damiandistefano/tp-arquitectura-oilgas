"""Load downloaded CSV sources into Bronze and metadata tables."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from .config import get_source_configs
from .db import build_insert_sql
from .logging_config import get_logger
from .postgres import connect_to_postgres, has_source_been_loaded, insert_rows
from .sources import download_source

logger = get_logger(__name__)


def _row_to_json(row: dict[str, str]) -> str:
    return json.dumps(row, ensure_ascii=True)


def build_bronze_rows(source, run_id: str):
    ingested_at = datetime.now(timezone.utc).isoformat()
    bronze_rows = []

    for index, row in enumerate(source.rows, start=1):
        bronze_rows.append(
            {
                "raw_payload": _row_to_json(row),
                "_run_id": run_id,
                "_source_name": source.name,
                "_source_url": source.url,
                "_source_file_hash": source.file_hash,
                "_ingested_at": ingested_at,
                "_raw_row_number": index,
            }
        )

    return bronze_rows


def build_pipeline_run(
    run_id: str,
    pipeline_name: str,
    status: str,
    error_message: str | None = None,
):
    timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "run_id": run_id,
        "pipeline_name": pipeline_name,
        "status": status,
        "started_at": timestamp,
        "finished_at": timestamp,
        "triggered_by": "manual",
        "parameters": json.dumps({}),
        "error_message": error_message,
    }


def build_source_file_record(
    run_id: str,
    source_name: str,
    source_url: str,
    source_file_hash: str,
    rows_loaded: int,
    target_table: str,
):
    return {
        "run_id": run_id,
        "source_name": source_name,
        "source_url": source_url,
        "source_file_hash": source_file_hash,
        "rows_loaded": rows_loaded,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "target_table": target_table,
    }


def build_source_payload(source, run_id: str, *, include_rows: bool = True):
    rows = build_bronze_rows(source, run_id) if include_rows else []
    return {
        "source_name": source.name,
        "source_url": source.url,
        "source_file_hash": source.file_hash,
        "rows": rows,
        "row_count": len(source.rows),
        "metadata": build_source_file_record(
            run_id,
            source.name,
            source.url,
            source.file_hash,
            len(source.rows),
            f"bronze.raw_{source.name}",
        ),
    }


def build_ingestion_payload(download_fn=download_source):
    run_id = str(uuid4())
    pipeline_name = "bronze_ingestion"

    logger.info("Starting ingestion run: %s", run_id)

    sources = [download_fn(cfg.name, cfg.url) for cfg in get_source_configs()]

    bronze_payload = {
        "run_id": run_id,
        "pipeline_run": build_pipeline_run(run_id, pipeline_name, "SUCCESS"),
        "sources": [],
    }

    for source in sources:
        logger.info(
            "Building payload for source: %s (%s rows)",
            source.name,
            len(source.rows),
        )

        bronze_payload["sources"].append(build_source_payload(source, run_id))

    logger.info("Payload built for run %s with %s source(s)", run_id, len(sources))
    return bronze_payload


def build_sql_statements(payload: dict) -> list[str]:
    statements = []

    pipeline_run = payload["pipeline_run"]
    statements.append(build_insert_sql("metadata.pipeline_runs", [pipeline_run]))

    for source in payload["sources"]:
        statements.append(build_insert_sql(source["metadata"]["target_table"], source["rows"]))
        statements.append(build_insert_sql("metadata.source_files", [source["metadata"]]))

    return [statement for statement in statements if statement]


def summarize_payload(payload: dict) -> dict:
    """
    Resume una corrida sin imprimir todas las filas cargadas.

    Parámetros:
        - payload: Payload completo de ingesta.

    Returns:
        Dict chico con run_id, estado y resumen por fuente.
    """
    return {
        "run_id": payload["run_id"],
        "status": payload["pipeline_run"]["status"],
        "sources": [
            {
                "source_name": source["source_name"],
                "source_file_hash": source["source_file_hash"],
                "rows": source.get("row_count", len(source["rows"])),
                "target_table": source["metadata"]["target_table"],
            }
            for source in payload["sources"]
        ],
    }


def persist_payload(payload: dict) -> None:
    """
    Persiste una corrida completa en Postgres.

    Inserta en batches para evitar queries gigantes. La metadata de archivos se
    registra después de cargar cada tabla Bronze, así no queda una fuente marcada
    como cargada si falla antes la carga real.
    """
    with connect_to_postgres() as conn:
        insert_rows("metadata.pipeline_runs", [payload["pipeline_run"]], conn=conn)

        for source in payload["sources"]:
            target_table = source["metadata"]["target_table"]
            source_name = source["source_name"]

            logger.info("Loading source %s into %s", source_name, target_table)

            insert_rows(target_table, source["rows"], conn=conn)
            insert_rows("metadata.source_files", [source["metadata"]], conn=conn)

            logger.info(
                "Source %s loaded into %s (%s row(s))",
                source_name,
                target_table,
                len(source["rows"]),
            )


def persist_ingestion(download_fn=download_source):
    run_id = str(uuid4())
    pipeline_name = "bronze_ingestion"
    logger.info("Starting ingestion run: %s", run_id)

    payload = {
        "run_id": run_id,
        "pipeline_run": build_pipeline_run(run_id, pipeline_name, "SUCCESS"),
        "sources": [],
    }
    sources_to_load = []
    skipped_sources = []

    for cfg in get_source_configs():
        source = download_fn(cfg.name, cfg.url)
        already_loaded = has_source_been_loaded(source.name, source.file_hash)

        if already_loaded:
            logger.info(
                "Skipping source %s - already loaded with hash %s",
                source.name,
                source.file_hash,
            )
            skipped_sources.append(source.name)
            payload["sources"].append(build_source_payload(source, run_id, include_rows=False))
            continue

        logger.info(
            "Building payload for source: %s (%s rows)",
            source.name,
            len(source.rows),
        )
        source_payload = build_source_payload(source, run_id)
        payload["sources"].append(source_payload)
        sources_to_load.append(source_payload)

    if not sources_to_load:
        logger.info("All sources already loaded, nothing to do")
        return payload

    payload_to_load = {
        "run_id": payload["run_id"],
        "pipeline_run": payload["pipeline_run"],
        "sources": sources_to_load,
    }

    if skipped_sources:
        logger.info(
            "Loading %s/%s sources. Skipped: %s",
            len(sources_to_load),
            len(payload["sources"]),
            ", ".join(skipped_sources),
        )

    persist_payload(payload_to_load)

    logger.info("Ingestion run %s completed successfully", payload["run_id"])
    return payload


def run_ingestion(download_fn=download_source):
    return persist_ingestion(download_fn=download_fn)


if __name__ == "__main__":
    result = persist_ingestion()
    print(json.dumps(summarize_payload(result), ensure_ascii=True, indent=2))
