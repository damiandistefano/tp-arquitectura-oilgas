# Indice de ADRs - Oil & Gas Data Platform

Este directorio registra decisiones de arquitectura del proyecto. Cada ADR debe explicar:

- que problema habia que resolver;
- que alternativas se consideraron;
- cual se eligio;
- que trade-offs deja;
- que queda fuera de alcance.

Un ADR que solo dice "usamos X" sin comparar alternativas queda incompleto para la defensa.

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

## Cobertura actual contra Adenda 2

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

## Criterio de cierre

Los ADRs cubren las decisiones obligatorias de la Fase 2 y tambien dejan documentado el trade-off de BI. La recomendacion para la entrega es no sumar ADRs nuevos salvo que haya una decision implementada y evidencia concreta para defenderla.
