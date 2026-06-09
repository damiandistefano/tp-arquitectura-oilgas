"""Load downloaded CSV sources into Bronze and metadata tables."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from .config import get_source_configs
from .db import build_insert_sql
from .logging_config import get_logger
from .postgres import execute_statements, has_source_been_loaded
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


def build_pipeline_run(run_id: str, pipeline_name: str, status: str, error_message: str | None = None):
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


def build_source_file_record(run_id: str, source_name: str, source_url: str, source_file_hash: str, rows_loaded: int, target_table: str):
    return {
        "run_id": run_id,
        "source_name": source_name,
        "source_url": source_url,
        "source_file_hash": source_file_hash,
        "rows_loaded": rows_loaded,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "target_table": target_table,
    }


def build_ingestion_payload(download_fn=download_source):
    run_id = str(uuid4())
    pipeline_name = "bronze_ingestion"
    logger.info(f"Starting ingestion run: {run_id}")
    sources = [download_fn(cfg.name, cfg.url) for cfg in get_source_configs()]

    bronze_payload = {
        "run_id": run_id,
        "pipeline_run": build_pipeline_run(run_id, pipeline_name, "SUCCESS"),
        "sources": [],
    }

    for source in sources:
        logger.info(
            f"Building payload for source: {source.name} ({len(source.rows)} rows)"
        )
        bronze_payload["sources"].append(
            {
                "source_name": source.name,
                "source_url": source.url,
                "source_file_hash": source.file_hash,
                "rows": build_bronze_rows(source, run_id),
                "metadata": build_source_file_record(
                    run_id,
                    source.name,
                    source.url,
                    source.file_hash,
                    len(source.rows),
                    f"bronze.raw_{source.name}",
                ),
            }
        )

    logger.info(f"Payload built for run {run_id} with {len(sources)} source(s)")
    return bronze_payload


def build_sql_statements(payload: dict) -> list[str]:
    statements = []

    pipeline_run = payload["pipeline_run"]
    statements.append(build_insert_sql("metadata.pipeline_runs", [pipeline_run]))

    for source in payload["sources"]:
        statements.append(build_insert_sql(source["metadata"]["target_table"], source["rows"]))
        statements.append(build_insert_sql("metadata.source_files", [source["metadata"]]))

    return [statement for statement in statements if statement]


def persist_ingestion(download_fn=download_source):
    payload = build_ingestion_payload(download_fn=download_fn)

    # Deduplication: skip sources that have already been loaded
    sources_to_load = []
    skipped_sources = []

    for source in payload["sources"]:
        if has_source_been_loaded(source["source_name"], source["source_file_hash"]):
            logger.info(
                f"Skipping source {source['source_name']} - already loaded with hash "
                f"{source['source_file_hash']}"
            )
            skipped_sources.append(source["source_name"])
        else:
            sources_to_load.append(source)

    if not sources_to_load:
        logger.info("All sources already loaded, nothing to do")
        return payload

    # Build statements only for sources to load
    payload_to_load = {
        "run_id": payload["run_id"],
        "pipeline_run": payload["pipeline_run"],
        "sources": sources_to_load,
    }

    if skipped_sources:
        logger.info(
            f"Loading {len(sources_to_load)}/{len(payload['sources'])} sources. "
            f"Skipped: {', '.join(skipped_sources)}"
        )

    statements = build_sql_statements(payload_to_load)
    execute_statements(statements)
    logger.info(f"Ingestion run {payload['run_id']} completed successfully")
    return payload


def run_ingestion(download_fn=download_source):
    return persist_ingestion(download_fn=download_fn)


if __name__ == "__main__":
    result = persist_ingestion()
    print(json.dumps(result, ensure_ascii=True, indent=2))
