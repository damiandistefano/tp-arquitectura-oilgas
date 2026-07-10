# Indice de ADRs - Oil & Gas Data Platform

Este directorio registra decisiones de arquitectura del proyecto. Cada ADR debe explicar:

- que problema habia que resolver;
- que alternativas se consideraron;
- cual se eligio;
- que trade-offs deja;
- que queda fuera de alcance.

Un ADR que solo dice "usamos X" sin comparar alternativas queda incompleto como registro de decision.

---

## Formato del equipo

```text
## Estado
## Contexto
## Problema
## Alternativas consideradas
## Decision
## Consecuencias
## Que queda fuera
```

El ultimo titulo puede variar, pero la idea no: toda decision importante debe mostrar limites y consecuencias.

---

## ADRs de Fase 1 - API, CI/CD y monitoreo

| # | Titulo | Estado | Area |
|---|---|---|---|
| [0001](0001-usar-docker-compose-para-stack-local.md) | Usar Docker Compose para stack local | Aceptado | Infraestructura |
| [0002](0002-usar-github-actions-para-ci.md) | Usar GitHub Actions para CI | Aceptado | CI/CD |
| [0003](0003-publicar-imagenes-en-ghcr.md) | Publicar imagenes Docker en GHCR | Aceptado | CI/CD |
| [0004](0004-usar-prometheus-grafana-alertmanager-para-monitoreo.md) | Usar Prometheus + Grafana + Alertmanager | Aceptado | Monitoreo |
| [0005](0005-usar-trivy-para-escaneo-de-vulnerabilidades.md) | Usar Trivy para escaneo de vulnerabilidades | Aceptado | Seguridad |

---

## ADRs de Fase 2 - Plataforma de datos

| # | Titulo | Estado | Area |
|---|---|---|---|
| [0006](0006-usar-dagster-para-orquestacion-de-datos.md) | Usar Dagster para orquestacion del pipeline | Aceptado | Orquestacion |
| [0007](0007-definir-estrategia-de-carga-y-backfill.md) | Estrategia de carga y backfill | Aceptado | Ingesta |
| [0008](0008-usar-postgres-como-warehouse-local.md) | Usar PostgreSQL como warehouse local | Aceptado | Almacenamiento |
| [0009](0009-usar-arquitectura-medallion-para-procesamiento.md) | Usar arquitectura Medallion para procesamiento | Aceptado | Datos |
| [0010](0010-usar-modelo-estrella-en-gold.md) | Usar modelo estrella en Gold | Aceptado | Datos |
| [0011](0011-persistir-calidad-de-datos-y-bloquear-promocion.md) | Persistir calidad de datos y bloquear promocion | Aceptado | Calidad |
| [0012](0012-usar-vistas-sql-como-semantic-layer.md) | Usar vistas SQL como semantic layer | Aceptado | BI / Semantic |
| [0013](0013-usar-datahub-para-gobierno-de-datos.md) | Usar DataHub para gobierno de datos | Aceptado | Governance |
| [0014](0014-usar-metabase-para-bi.md) | Usar Metabase para BI | Aceptado | BI |

---

## ADRs de Fase 3 - ML Engineering

| # | Titulo | Estado | Area |
|---|---|---|---|
| [0015](0015-definir-target-y-grano-de-forecasting.md) | Definir target y grano de forecasting | Aceptado | Modelo |
| [0016](0016-usar-mlflow-para-tracking-y-registry.md) | Usar MLflow para tracking y registry | Aceptado | Tracking |
| [0017](0017-usar-postgres-como-feature-store.md) | Usar Postgres como feature store | Aceptado | Feature store |
| [0018](0018-definir-modelo-baseline-y-gate-de-promocion.md) | Definir modelo, baseline y gate de promocion | Aceptado | Modelo |
| [0019](0019-orquestar-retraining-con-dagster-vs-airflow.md) | Orquestar el retraining con Dagster | Aceptado | Orquestacion |
| [0020](0020-servir-modelo-con-fastapi-feature-enrichment-y-adapter.md) | Servir modelo con FastAPI, feature enrichment y adapter | Aceptado | Model serving |
| [0021](0021-ci-con-fixture-chico-para-pipeline-ml.md) | CI con fixture chico para el pipeline de ML | Aceptado | CI/CD |
| [0022](0022-registrar-prediction-logs-en-postgres.md) | Registrar prediction logs en Postgres | Aceptado | Observabilidad |
| [0023](0023-drift-check-minimo-sin-monitoring-productivo.md) | Drift check minimo, sin monitoring productivo | Aceptado | Observabilidad |

---

## Cobertura de requerimientos de Fase 2 (data platform)

| Decision pedida o esperada | ADR que la cubre | Nota |
|---|---|---|
| Orquestador con DAGs/assets como codigo | 0006 | Dagster, comparado contra Airflow, Prefect y scripts. |
| Tipo de carga y estrategia de reprocesamiento | 0007 | Full download + Bronze append-only con hash. Backfill queda acotado por fuente CSV estatica. |
| Warehouse local/sandbox | 0008 | PostgreSQL por compatibilidad con dbt, Metabase y stack Docker. |
| Arquitectura Medallion | 0009 | Bronze/Silver/Gold/Semantic. |
| Modelo dimensional | 0010 | Fact table, dimensiones, grano, surrogate keys y SCD tipo 1. |
| Calidad de datos persistida | 0011 | Tabla `quality.data_quality_results`, severidad y exit code operativo. |
| Semantic layer | 0012 | Vistas SQL versionadas para Metabase. |
| Gobierno de datos y catalogo | 0013 | DataHub en EC2 dedicada, comparado contra OpenMetadata, Amundsen y dbt Docs. |
| BI para usuarios no tecnicos | 0014 | Metabase, comparado contra Grafana y Superset. |

## Cobertura de requerimientos de Fase 3 (ML Engineering)

| Requerimiento / decision Fase 3 | ADR que lo cubre | Evidencia |
|---|---|---|
| Feature store persistido y usado en inferencia | [0017](0017-usar-postgres-como-feature-store.md) | Schema `features` (`postgres-init/02_features_schema.sql`), `ml/build_features.py`, lookup de inferencia en `app/feature_lookup.py` |
| Training reproducible (target, grano y contrato) | [0015](0015-definir-target-y-grano-de-forecasting.md), [0018](0018-definir-modelo-baseline-y-gate-de-promocion.md) | `docs/contracts.md`, `ml/train.py` con split temporal y baseline `prod_pet_lag_1` |
| Validation / promotion gate | [0018](0018-definir-modelo-baseline-y-gate-de-promocion.md) | `ml/promotion_gate.py`, `gate_decision.json` por run, assert `promoted=true` en `scripts/data-ml-ci-smoke.sh` |
| Orquestacion / retraining recurrente y por dia dado | [0019](0019-orquestar-retraining-con-dagster-vs-airflow.md) | `dagster/dwh_pipeline/definitions.py` (`ml_training_job`, `ml_retraining_monthly`), `scripts/retrain-model.sh` |
| Experiment tracking | [0016](0016-usar-mlflow-para-tracking-y-registry.md) | Servicio `mlflow` en `docker-compose.yml`, runs logueados por `ml/train.py`, `scripts/mlflow-smoke.sh` |
| Model registry versionado | [0016](0016-usar-mlflow-para-tracking-y-registry.md) | Modelo `oilgas_forecaster` con alias `champion`, verificacion de alias en `scripts/data-ml-ci-smoke.sh` |
| API serving del modelo validado | [0020](0020-servir-modelo-con-fastapi-feature-enrichment-y-adapter.md) | `app/api.py` (`/api/v1/forecast`), adapter `app/model_registry.py` con fallback visible, `scripts/api-forecast-smoke.sh` |
| Prediction logs | [0022](0022-registrar-prediction-logs-en-postgres.md) | `app/prediction_logging.py`, tabla `metadata.prediction_logs` |
| Drift / observabilidad ML | [0023](0023-drift-check-minimo-sin-monitoring-productivo.md) | `ml/drift_check.py` (z-score y `drifted` por feature), `scripts/run-drift-check.sh`, `features.feature_reference_stats` |
| CI/CD del pipeline ML | [0021](0021-ci-con-fixture-chico-para-pipeline-ml.md) | `.github/workflows/ml-ci.yml`, `scripts/data-ml-ci-smoke.sh`, fixture `tests/fixtures/ml_ci_fixture.sql` |

## Criterio de cierre

Los ADRs cubren las decisiones clave de Fase 2 y Fase 3. Solo deberian sumarse
ADRs nuevos si aparece una decision tecnica implementada, con trade-offs reales
y evidencia concreta para sostenerla.
