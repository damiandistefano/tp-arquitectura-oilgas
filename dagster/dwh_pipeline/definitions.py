"""Punto de entrada de Dagster: assets, jobs y schedules."""

from dagster import (
    AssetSelection,
    Definitions,
    RunRequest,
    ScheduleDefinition,
    define_asset_job,
    in_process_executor,
    schedule,
)

from .assets import (
    build_features,
    extract_to_bronze,
    promote_model,
    run_quality_checks,
    run_silver_transformations,
    train_model,
)

data_pipeline_job = define_asset_job(
    name="data_pipeline_job",
    selection=AssetSelection.assets(
        extract_to_bronze, run_silver_transformations, run_quality_checks
    ),
    description="Ingesta a Bronze + dbt (Silver/Gold) + checks de calidad.",
)

ml_training_job = define_asset_job(
    name="ml_training_job",
    selection=AssetSelection.assets(build_features, train_model, promote_model),
    description="Features -> training -> gate de promoción con bootstrap.",
)

data_pipeline_schedule = ScheduleDefinition(
    name="data_pipeline_daily",
    job=data_pipeline_job,
    cron_schedule="0 5 * * *",
    execution_timezone="America/Argentina/Buenos_Aires",
)


@schedule(
    name="ml_retraining_monthly",
    job=ml_training_job,
    cron_schedule="0 7 5 * *",
    execution_timezone="America/Argentina/Buenos_Aires",
)
def ml_retraining_monthly(context):
    """Reentrena el día 5 de cada mes con as_of_date = fecha de ejecución.

    Para repetir el entrenamiento de un día puntual, lanzar ml_training_job
    desde el launchpad con otro as_of_date en la config de los assets.
    """
    as_of_date = context.scheduled_execution_time.date().isoformat()
    return RunRequest(
        run_key=f"ml-retraining-{as_of_date}",
        run_config={
            "ops": {
                "build_features": {"config": {"as_of_date": as_of_date}},
                "train_model": {"config": {"as_of_date": as_of_date}},
            }
        },
    )


defs = Definitions(
    assets=[
        extract_to_bronze,
        run_silver_transformations,
        run_quality_checks,
        build_features,
        train_model,
        promote_model,
    ],
    jobs=[data_pipeline_job, ml_training_job],
    schedules=[data_pipeline_schedule, ml_retraining_monthly],
    executor=in_process_executor,
)
