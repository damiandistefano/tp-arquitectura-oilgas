# Runbook BI user

Este runbook explica cómo consultar las métricas analíticas disponibles para usuarios de negocio.

## Objetivo

Permitir que un usuario no técnico revise producción mensual, producción por operadora, producción por área/yacimiento, cantidad de pozos y frescura de datos.

## Fuente de datos para BI

Las consultas de BI deben usar las vistas de la capa semantic:

- semantic.vw_produccion_mensual
- semantic.vw_produccion_por_operadora
- semantic.vw_produccion_por_area
- semantic.vw_frescura_datos

Estas vistas ya agregan métricas y evitan consultar directamente las tablas Gold.

## Dashboard mínimo sugerido

El dashboard debería incluir:

- producción mensual total
- producción por operadora
- producción por área y yacimiento
- cantidad de pozos con producción
- última ingesta disponible
- último período disponible
- estado de calidad de la última corrida

## Conexión desde Metabase

Cuando Metabase esté disponible en el stack, se debe conectar a Postgres con estos datos:

- host: postgres
- port: 5432
- database: warehouse
- user: dwh
- password: dwh

Para conexión local desde la máquina host:

- host: localhost
- port: 5433
- database: warehouse
- user: dwh
- password: dwh

## Consultas de validación

Producción mensual:

    select * from semantic.vw_produccion_mensual limit 20;

Producción por operadora:

    select * from semantic.vw_produccion_por_operadora limit 20;

Producción por área/yacimiento:

    select * from semantic.vw_produccion_por_area limit 20;

Frescura de datos:

    select * from semantic.vw_frescura_datos;

Estado de calidad:

    select check_name, dimension, status, severity, rows_failed from quality.data_quality_results order by executed_at desc limit 20;

## Si algo falla

Si una vista semantic no existe, primero correr:

    cd dbt
    dbt run
    dbt test
    cd ..

Si no hay resultados de calidad, correr:

    bash scripts/run-quality-checks.sh

Si Metabase no está levantado, se pueden validar las mismas consultas con psql contra Postgres.

## Nota de alcance

El modelo analítico y las vistas semantic ya están disponibles. La publicación visual en Metabase depende de que el servicio Metabase esté agregado y levantado en el stack Docker.
