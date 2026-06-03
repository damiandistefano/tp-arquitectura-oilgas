"""Load downloaded CSV sources into Bronze and metadata tables."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from .config import get_source_configs
from .db import build_insert_sql
from .sources import download_source


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
    sources = [download_fn(cfg.name, cfg.url) for cfg in get_source_configs()]

    bronze_payload = {
        "run_id": run_id,
        "pipeline_run": build_pipeline_run(run_id, pipeline_name, "SUCCESS"),
        "sources": [],
    }

    for source in sources:
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

    return bronze_payload


def build_sql_statements(payload: dict) -> list[str]:
    statements = []

    pipeline_run = payload["pipeline_run"]
    statements.append(build_insert_sql("metadata.pipeline_runs", [pipeline_run]))

    for source in payload["sources"]:
        statements.append(build_insert_sql(source["metadata"]["target_table"], source["rows"]))
        statements.append(build_insert_sql("metadata.source_files", [source["metadata"]]))

    return [statement for statement in statements if statement]


def run_ingestion(download_fn=download_source):
    return build_ingestion_payload(download_fn=download_fn)


if __name__ == "__main__":
    result = run_ingestion()
    print(json.dumps(result, ensure_ascii=True, indent=2))
