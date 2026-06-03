from pathlib import Path

from extract.load_to_bronze import (
    build_bronze_rows,
    build_ingestion_payload,
    build_pipeline_run,
    build_source_file_record,
    build_sql_statements,
)
from extract.sources import load_csv_from_path


def test_load_csv_from_path_parses_headers_and_rows(tmp_path: Path):
    csv_path = tmp_path / "source.csv"
    csv_path.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")

    source = load_csv_from_path(csv_path, name="demo", url="https://example.com/demo.csv")

    assert source.headers == ["a", "b"]
    assert source.rows == [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}]
    assert source.file_hash


def test_build_bronze_rows_adds_metadata():
    class DummySource:
        name = "demo"
        url = "https://example.com/demo.csv"
        file_hash = "hash"
        rows = [{"a": "1"}]

    rows = build_bronze_rows(DummySource, run_id="run-1")

    assert rows[0]["_run_id"] == "run-1"
    assert rows[0]["_source_name"] == "demo"
    assert rows[0]["_raw_row_number"] == 1


def test_build_metadata_records():
    run = build_pipeline_run("run-1", "bronze_ingestion", "SUCCESS")
    source_file = build_source_file_record("run-1", "demo", "https://example.com/demo.csv", "hash", 2, "bronze.raw_demo")

    assert run["status"] == "SUCCESS"
    assert source_file["rows_loaded"] == 2
    assert source_file["target_table"] == "bronze.raw_demo"


def test_build_ingestion_payload_uses_download_fn(monkeypatch):
    monkeypatch.setenv("PRODUCCION_SOURCE_URL", "https://example.com/produccion.csv")
    monkeypatch.setenv("POZOS_SOURCE_URL", "https://example.com/pozos.csv")

    class DummySource:
        def __init__(self, name, url):
            self.name = name
            self.url = url
            self.file_hash = f"hash-{name}"
            self.rows = [{"a": "1"}]

    calls = []

    def fake_download(name, url):
        calls.append((name, url))
        return DummySource(name, url)

    payload = build_ingestion_payload(download_fn=fake_download)

    assert len(calls) == 2
    assert payload["pipeline_run"]["status"] == "SUCCESS"
    assert len(payload["sources"]) == 2


def test_build_sql_statements_includes_metadata_and_bronze():
    payload = {
        "pipeline_run": build_pipeline_run("run-1", "bronze_ingestion", "SUCCESS"),
        "sources": [
            {
                "metadata": {
                    "run_id": "run-1",
                    "source_name": "demo",
                    "source_url": "https://example.com/demo.csv",
                    "source_file_hash": "hash",
                    "rows_loaded": 1,
                    "ingested_at": "2026-01-01T00:00:00+00:00",
                    "target_table": "bronze.raw_demo",
                },
                "rows": [
                    {
                        "raw_payload": '{"a": "1"}',
                        "_run_id": "run-1",
                        "_source_name": "demo",
                        "_source_url": "https://example.com/demo.csv",
                        "_source_file_hash": "hash",
                        "_ingested_at": "2026-01-01T00:00:00+00:00",
                        "_raw_row_number": 1,
                    }
                ],
            }
        ],
    }

    statements = build_sql_statements(payload)

    assert any("metadata.pipeline_runs" in statement for statement in statements)
    assert any("metadata.source_files" in statement for statement in statements)
    assert any("bronze.raw_demo" in statement for statement in statements)
