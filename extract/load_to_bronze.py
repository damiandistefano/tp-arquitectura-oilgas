"""Load downloaded CSV sources into Bronze and metadata tables."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from .config import get_source_configs
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
    return {
        "run_id": run_id,
        "pipeline_name": pipeline_name,
        "status": status,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
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


def run_ingestion(download_fn=download_source):
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


if __name__ == "__main__":
    result = run_ingestion()
    print(json.dumps(result, ensure_ascii=True, indent=2))
