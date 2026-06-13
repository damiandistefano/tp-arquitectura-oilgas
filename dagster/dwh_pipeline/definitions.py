"""Punto de entrada de Dagster."""

from dagster import Definitions, in_process_executor
from .assets import extract_to_bronze, run_silver_transformations, run_quality_checks

defs = Definitions(
    assets=[extract_to_bronze, run_silver_transformations, run_quality_checks],
    executor=in_process_executor,
)
