from pathlib import Path

from extract.load_to_bronze import build_bronze_rows, build_pipeline_run, build_source_file_record, run_ingestion
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


def test_run_ingestion_uses_download_fn():
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

    payload = run_ingestion(download_fn=fake_download)

    assert len(calls) == 2
    assert payload["pipeline_run"]["status"] == "SUCCESS"
    assert len(payload["sources"]) == 2
