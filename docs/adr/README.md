# Índice de ADRs — Oil & Gas Data Platform

Registro de decisiones de arquitectura del proyecto. Cada ADR documenta una decisión técnica
relevante: por qué se tomó, qué alternativas se descartaron y qué consecuencias tiene.

## Convención de formato del equipo

Todos los ADRs siguen este esquema:

```
## Estado
## Contexto
## Problema
## Alternativas consideradas
## Decisión
## Consecuencias
```

Un ADR sin "Alternativas consideradas" se considera incompleto — la decisión no es defendible si
no queda claro qué se descartó y por qué.

---

## ADRs de Fase 1 — API, CI/CD y monitoreo

| # | Título | Estado | Área | Review |
|---|---|---|---|---|
| [0001](0001-usar-docker-compose-para-stack-local.md) | Usar Docker Compose para stack local | Aceptado | Infraestructura | ✅ Compara K8s, Vagrant y Docker standalone |
| [0002](0002-usar-github-actions-para-ci.md) | Usar GitHub Actions para CI | Aceptado | CI/CD | ✅ Compara GitLab CI, Jenkins, CircleCI |
| [0003](0003-publicar-imagenes-en-ghcr.md) | Publicar imágenes Docker en GHCR | Aceptado | CI/CD | ✅ Compara Docker Hub, ECR, build en EC2 |
| [0004](0004-usar-prometheus-grafana-alertmanager-para-monitoreo.md) | Usar Prometheus + Grafana + Alertmanager | Aceptado | Monitoreo | ✅ Compara Datadog/New Relic, ELK/Loki |
| [0005](0005-usar-trivy-para-escaneo-de-vulnerabilidades.md) | Usar Trivy para escaneo de vulnerabilidades | Aceptado | Seguridad | ✅ Compara Snyk, Anchore, Clair |

---

## ADRs de Fase 2 — Plataforma de datos (Adenda 2)

| # | Título | Estado | Área | Review |
|---|---|---|---|---|
| 0006 | *(pendiente — Integrante 1: orquestación / Dagster)* | ⏳ Falta | Orquestación | — |
| 0007 | *(pendiente — Integrante 1: estrategia de carga / backfill)* | ⏳ Falta | Ingesta | — |
| 0008 | *(pendiente — Integrante 1: warehouse PostgreSQL)* | ⏳ Falta | Almacenamiento | — |
| [0009](0009-usar-arquitectura-medallion-para-procesamiento.md) | Usar arquitectura medallion para procesamiento | Aceptado | Datos | ✅ Compara Lambda, Kappa, flat staging |
| [0010](0010-usar-modelo-estrella-en-gold.md) | Usar modelo estrella en Gold | Aceptado | Datos | ✅ Compara OBT y modelo normalizado |
| [0011](0011-persistir-calidad-de-datos-y-bloquear-promocion.md) | Persistir calidad de datos y bloquear promoción | Aceptado | Calidad | ✅ Compara dbt tests, Great Expectations |
| [0012](0012-usar-vistas-sql-como-semantic-layer.md) | Usar vistas SQL como semantic layer | Aceptado | BI / Semantic | ✅ Compara Cube, dbt Semantic Layer |
| [0013](0013-usar-datahub-para-gobierno-de-datos.md) | Usar DataHub para gobierno de datos | Aceptado | Governance | ✅ Compara OpenMetadata, Amundsen, dbt docs |
| 0014 | *(pendiente — Integrante 2: BI / Metabase)* | ⏳ Falta | BI | — |

---

## Notas de review (Integrante 3)

### Fase 1 (0001–0005)
- Todos comparan alternativas con pros y contras concretos. Cumplen el formato del equipo.
- Fueron reescritos en la rama `feature/phase1-delivery-access-fixes` para corregir el feedback de
  Fase 1 ("ADRs demasiado pulidos / olor a IA sin alternativas defendibles").
- Tono: voz propia, sin cierres buzzword. Mencionan qué queda fuera del alcance de cada decisión.

### Fase 2 (0009–0012)
- Escritos directamente en el estilo correcto (Integrante 2). No necesitaron corrección.
- 0009 es el más completo: contexto operativo real, diagrama textual de capas, consecuencias con
  trade-offs concretos.
- 0011 es sólido en la parte de consecuencia operativa (exit code + bloqueo aguas abajo).
- 0012 es conciso y honesto sobre lo que no implementa (sin oversell de la semantic layer).

### Gaps pendientes
- **0006–0008**: son responsabilidad de Integrante 1. Falta documentar las decisiones de orquestación
  (Dagster vs Airflow vs Prefect), estrategia de carga/backfill (append-only bronze, upsert silver/gold)
  y elección de PostgreSQL como warehouse.
- **0013**: DataHub. Escrito. Compara OpenMetadata, Amundsen y dbt docs; decide DataHub en EC2
  dedicada on-demand. Deploy documentado en `docs/runbooks/datahub.md`.
- **0014**: Metabase. Falta la decisión de BI (Metabase vs Grafana vs Superset).
