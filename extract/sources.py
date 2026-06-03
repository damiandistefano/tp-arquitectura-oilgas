"""Download and normalize raw CSV sources."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from hashlib import sha256
from io import StringIO
from pathlib import Path
from urllib.request import urlopen


@dataclass(frozen=True)
class DownloadedSource:
    name: str
    url: str
    file_hash: str
    headers: list[str]
    rows: list[dict[str, str]]


def _parse_csv(text: str) -> tuple[list[str], list[dict[str, str]]]:
    buffer = StringIO(text)
    reader = csv.DictReader(buffer)
    if reader.fieldnames is None:
        raise ValueError("CSV source is empty")

    headers = [header.strip() for header in reader.fieldnames if header]
    if not headers:
        raise ValueError("CSV source does not contain headers")

    rows: list[dict[str, str]] = []
    for row in reader:
        rows.append({header: (row.get(header) or "").strip() for header in headers})

    return headers, rows


def download_source(name: str, url: str) -> DownloadedSource:
    raw_bytes = urlopen(url, timeout=60).read()
    if not raw_bytes:
        raise ValueError(f"Empty payload for source: {name}")

    file_hash = sha256(raw_bytes).hexdigest()
    headers, rows = _parse_csv(raw_bytes.decode("utf-8-sig"))
    return DownloadedSource(name=name, url=url, file_hash=file_hash, headers=headers, rows=rows)


def load_csv_from_path(path: str | Path, name: str, url: str) -> DownloadedSource:
    raw_bytes = Path(path).read_bytes()
    if not raw_bytes:
        raise ValueError(f"Empty payload for source: {name}")

    file_hash = sha256(raw_bytes).hexdigest()
    headers, rows = _parse_csv(raw_bytes.decode("utf-8-sig"))
    return DownloadedSource(name=name, url=url, file_hash=file_hash, headers=headers, rows=rows)
