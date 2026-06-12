"""Assets del pipeline de datos."""

import subprocess
import sys

from dagster import Backoff, RetryPolicy, asset, get_dagster_logger

_WORKSPACE = "/workspace"


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

    result = subprocess.run(
        ["dbt", "build", "--project-dir", f"{_WORKSPACE}/dbt", "--profiles-dir", f"{_WORKSPACE}/dbt"],
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
