# Runbook dbt analytics

Pasos para correr la transformacion desde Bronze hasta Silver, Gold y Semantic usando dbt.

## Requisitos

- Docker Desktop corriendo.
- Postgres levantado con docker compose.
- Datos Bronze cargados.
- Dependencias instaladas con requirements-dev.txt.

## Preparar entorno

    python -m pip install -r requirements-dev.txt
    mkdir -p ~/.dbt
    cp dbt/profiles.example.yml ~/.dbt/profiles.yml

## Levantar Postgres

    docker compose up -d postgres
    docker compose ps

## Cargar Bronze

    set -a
    source .env.example
    set +a
    export POSTGRES_HOST=localhost
    export POSTGRES_PORT=5433
    bash scripts/run-data-pipeline.sh

Counts esperados en Bronze:

- bronze.raw_produccion_no_convencional: 405996
- bronze.raw_pozos_operadoras: 84242
- metadata.source_files: 2

## Correr dbt

    cd dbt
    dbt debug
    dbt run
    dbt test
    cd ..

## Counts esperados

Silver:

- silver.produccion_no_convencional: 405996
- silver.pozos_operadoras: 84242

Gold:

- gold.fact_produccion_pozo: 405996
- gold.dim_pozo: 84538
- gold.dim_fecha: 244
- gold.dim_operadora: 55

Semantic:

- semantic.vw_produccion_mensual: 244
- semantic.vw_produccion_por_operadora: 4395

## Validaciones generales

    python -m pytest -q
    python -m ruff check .
