# ADR 0021 — CI con fixture chico para el pipeline de ML

## Estado
Aceptado

## Contexto

Adenda 3 pide que el pipeline de ML tenga CI, no solo la API. El pipeline completo (features -> train -> gate -> API -> logs) depende de tener datos de producción cargados en `gold`, pero esos datos vienen de descargar CSVs grandes de datos.energia.gob.ar, cosa que no queremos hacer en cada corrida de GitHub Actions.

## Problema

Necesitamos que el CI:
- pruebe el pipeline de ML de punta a punta, no solo tests unitarios sueltos
- no dependa de bajar los datasets grandes ni de que la fuente externa esté disponible
- sea rápido, para no hacer el CI insoportablemente lento

## Alternativas consideradas

**Correr el pipeline real de ingesta en CI (bajar los CSV)**
- Prueba el caso más realista
- Depende de una fuente externa que puede estar caída o tardar, lo que rompe el CI por motivos ajenos al código
- Tarda mucho más de lo razonable para un check de cada PR

**Solo tests unitarios con mocks, sin levantar nada real**
- Es rápido
- No prueba que el pipeline funcione contra una base Postgres real, ni que build_features/train/gate se puedan ejecutar en conjunto
- Deja afuera bugs de integración (por ejemplo, columnas que no coinciden entre lo que escribe build_features y lo que lee train)

**Fixture chico insertado directo en gold (elegida)**
- Un script SQL mete a mano un par de pozos con unos meses de historia directo en `gold.fact_produccion_pozo` y `gold.dim_pozo`, sin pasar por bronze/silver/dbt
- El pipeline real (build_features -> train -> gate -> API -> drift check) corre igual que en producción, solo que sobre datos chicos e inventados
- Es rápido y no depende de nada externo

## Decisión

Se agrega `tests/fixtures/ml_ci_fixture.sql` con dos pozos y trece meses de historia, y un script (`scripts/data-ml-ci-smoke.sh`) que encadena el pipeline completo sobre ese fixture. Un workflow nuevo (`.github/workflows/ml-ci.yml`) levanta Postgres, MLflow y la API reales en cada push/PR y corre ese script.

Como el fixture es chico y los datos son simples, el modelo puede no superar al baseline naive y el gate puede no promover nada. Esto no se trata como una falla del CI: lo que se valida es que el pipeline corre sin romperse y que el gate toma una decisión válida, no que gane un modelo específico.

## Consecuencias

- El CI de ML no depende de la fuente externa de datos.energia.gob.ar
- Corre rápido porque son pocas filas
- No prueba el volumen real de datos ni corridas de dbt, eso se prueba aparte con el `data-smoke.sh` existente cuando se corre el pipeline completo

## Qué queda fuera

No se corre dbt ni la ingesta real dentro de este CI. No se valida la calidad de un modelo entrenado con este fixture, solo que el pipeline mecánicamente funciona.
