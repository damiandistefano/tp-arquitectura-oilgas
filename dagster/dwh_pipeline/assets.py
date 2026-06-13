"""Assets del pipeline de datos."""

import os
from pathlib import Path
import subprocess
import sys

from dagster import Backoff, RetryPolicy, asset, get_dagster_logger

_WORKSPACE = "/workspace"
_DBT_PROJECT_DIR = f"{_WORKSPACE}/dbt"
_DBT_PROFILES_DIR = "/tmp/dbt-profiles"
_DBT_TARGET_DIR = "/tmp/dbt-target"
_DBT_LOG_DIR = "/tmp/dbt-logs"


def _write_dbt_profile() -> str:
    """Create a writable dbt profile for the Dagster container."""
    profile_dir = Path(_DBT_PROFILES_DIR)
    profile_dir.mkdir(parents=True, exist_ok=True)

    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    dbname = os.getenv("POSTGRES_DB", "warehouse")
    user = os.getenv("POSTGRES_USER", "dwh")
    password = os.getenv("POSTGRES_PASSWORD", "dwh")

    profile = f"""oilgas_analytics:
  target: local
  outputs:
    local:
      type: postgres
      host: {host}
      port: {port}
      user: {user}
      password: {password}
      dbname: {dbname}
      schema: analytics
      threads: 4
"""

    (profile_dir / "profiles.yml").write_text(profile, encoding="utf-8")
    return str(profile_dir)


@asset(
    name="extract_to_bronze",
    retry_policy=RetryPolicy(
        max_retries=3,
        delay=30,
        backoff=Backoff.EXPONENTIAL,
    ),
    description="Descarga las fuentes de datos.gob.ar y carga las tablas Bronze con metadata de corrida.",
    group_name="ingesta",
)
def extract_to_bronze():
    log = get_dagster_logger()
    log.info("Iniciando ingesta a Bronze")

    if _WORKSPACE not in sys.path:
        sys.path.insert(0, _WORKSPACE)

    from extract.load_to_bronze import run_ingestion  # noqa: PLC0415

    result = run_ingestion()
    log.info("Ingesta completada: run_id=%s", result["run_id"])
    return result["run_id"]


@asset(
    name="run_silver_transformations",
    deps=["extract_to_bronze"],
    description="Corre los modelos dbt para construir Silver y Gold desde Bronze.",
    group_name="transformaciones",
)
def run_silver_transformations():
    log = get_dagster_logger()
    log.info("Corriendo modelos dbt (silver + gold)")
    profiles_dir = _write_dbt_profile()

    result = subprocess.run(
        [
            "dbt",
            "build",
            "--project-dir",
            _DBT_PROJECT_DIR,
            "--profiles-dir",
            profiles_dir,
            "--target-path",
            _DBT_TARGET_DIR,
            "--log-path",
            _DBT_LOG_DIR,
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    log.info(result.stdout)
    if result.returncode != 0:
        log.error(result.stderr)
        raise RuntimeError(f"dbt build falló:\n{result.stderr}")

    log.info("dbt build completado")


@asset(
    name="run_quality_checks",
    deps=["run_silver_transformations"],
    description="Corre los checks de calidad y persiste los resultados en quality.data_quality_results.",
    group_name="calidad",
)
def run_quality_checks():
    log = get_dagster_logger()
    log.info("Corriendo checks de calidad")

    result = subprocess.run(
        [sys.executable, "-m", "quality.checks"],
        capture_output=True,
        text=True,
        cwd=_WORKSPACE,
        check=False,
    )

    log.info(result.stdout)
    if result.returncode != 0:
        log.error(result.stderr)
        raise RuntimeError(f"Quality checks fallaron:\n{result.stderr}")

    log.info("Checks de calidad completados")
