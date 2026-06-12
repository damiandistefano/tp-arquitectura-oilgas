# ADR 0006 — Usar Dagster para orquestación del pipeline de datos

## Estado
Aceptado

## Contexto

El pipeline de datos necesita correr en orden: primero descargar y cargar Bronze, después transformar con dbt, después correr calidad. Hay que poder ver si una corrida falló, reintentar sin duplicar datos, y eventualmente correr backfills. Sin orquestador esto se maneja con scripts bash encadenados, lo que hace difícil ver qué pasó en cada corrida.

## Problema

Necesitamos algo que:
- Ordene y ejecute los pasos del pipeline
- Tenga retries automáticos si falla una descarga
- Muestre en algún lugar el historial de corridas y su estado
- No sea demasiado pesado para levantar en una EC2 chica

## Alternativas consideradas

**Airflow**
- Es el más conocido del mercado para este tipo de pipelines
- Requiere varios servicios extra (scheduler, worker, webserver, base de datos propia)
- Consume bastante RAM, en una EC2 t3.small empieza a apretar
- La configuración inicial es lenta

**Prefect**
- Más moderno que Airflow, API más limpia
- En la versión cloud-hosted es muy cómodo, pero en self-hosted requiere un servidor de orquestación aparte
- Para uso local es válido pero tiene menos ejemplos en los prácticos de la materia

**Dagster**
- Se levanta con un solo proceso (`dagster dev`)
- Tiene UI web integrada sin servicios extra
- El modelo de "assets" (en lugar de DAGs de tareas) encaja bien con la arquitectura medallion: cada capa es un asset que depende del anterior
- El práctico de la materia lo usa, así que hay documentación de referencia
- Retries con backoff configurables por asset

**Scripts bash puros**
- Sin orquestador, solo `run-data-pipeline.sh`
- No hay UI, no hay historial, si algo falla hay que revisar logs a mano
- Válido para casos muy simples, pero no cumple los requisitos de la entrega

## Decisión

Usamos Dagster. Se levanta con un Dockerfile propio y queda accesible en el puerto 3002. Los assets del pipeline son `extract_to_bronze`, `run_silver_transformations` y `run_quality_checks`. El código de ingesta que ya existe en `extract/` no se reescribe, Dagster simplemente lo llama.

## Consecuencias

- La UI de Dagster en `:3002` muestra el estado de cada corrida y el grafo de dependencias entre assets
- Los retries están configurados en el asset, no en el script
- Agregar un nuevo paso al pipeline es agregar un asset nuevo en `dagster/dwh_pipeline/assets.py`
- El contenedor de Dagster necesita acceso al código de `extract/`, `dbt/` y `quality/`, que se montan como volúmenes
- Dagster guarda su propio estado en memoria (modo dev), no persiste historial entre reinicios del contenedor — aceptable para sandbox académico

## Qué queda fuera

No usamos Dagster Cloud ni modo producción con PostgreSQL backend para Dagster. Para esta entrega el modo `dev` es suficiente.
