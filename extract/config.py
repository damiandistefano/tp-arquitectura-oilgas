"""Centralized ingestion config."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class SourceConfig:
    name: str
    url: str
    target_table: str


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required env var: {name}")
    return value


def get_source_configs() -> list[SourceConfig]:
    return [
        SourceConfig(
            name="produccion_no_convencional",
            url=_require_env("PRODUCCION_SOURCE_URL"),
            target_table="bronze.raw_produccion_no_convencional",
        ),
        SourceConfig(
            name="pozos_operadoras",
            url=_require_env("POZOS_SOURCE_URL"),
            target_table="bronze.raw_pozos_operadoras",
        ),
    ]


def get_retry_count() -> int:
    return int(os.getenv("DATA_PIPELINE_RETRIES", "3"))


def get_retry_backoff_seconds() -> int:
    return int(os.getenv("DATA_PIPELINE_RETRY_BACKOFF_SECONDS", "30"))
