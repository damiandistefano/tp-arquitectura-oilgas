# Oil & Gas Predictive Platform

Plataforma end-to-end de datos y MLOps para forecast mensual de producción de petróleo por pozo, construida sobre datos públicos del sector energético argentino (datos.gob.ar).

Trabajo Práctico de Arquitectura de Software — implementación completa y reproducible de una data platform con capa de ML Engineering, pensada como arquitectura de referencia local-first (no como despliegue productivo con alta disponibilidad o multiambiente).

## Arquitectura

El proyecto está organizado en tres fases que se integran en un único flujo, de datos públicos a forecast servido por API:

```text
datos.gob.ar
  -> Bronze (ingesta append-only con hash de archivo)
  -> Silver (limpieza y tipado con dbt)
  -> Gold (modelo estrella: fact_produccion_pozo + dimensiones)
  -> Semantic (vistas SQL para BI)
  -> Feature Store (features.pozo_monthly_features)
  -> Training / Validation (baseline naive + split temporal)
  -> MLflow (Tracking + Model Registry, alias champion)
  -> Promotion Gate (promueve el modelo solo si mejora al baseline/champion)
  -> FastAPI Forecast (GET /api/v1/forecast)
  -> Prediction Logs + Drift Check
```

| Fase | Foco | Stack principal |
|---|---|---|
| 1 — Plataforma base | API REST, contenedores, CI/CD, monitoreo | FastAPI, Docker, GitHub Actions, GHCR, Prometheus/Grafana |
| 2 — Data Platform | Warehouse, orquestación, calidad, BI, gobierno | PostgreSQL, Dagster, dbt, Metabase, DataHub |
| 3 — ML Engineering | Feature store, training, serving, drift | MLflow, scikit-learn, promotion gate, drift check |

## Stack técnico

Python · FastAPI · PostgreSQL · Dagster · dbt · MLflow · scikit-learn · Docker Compose · GitHub Actions · Prometheus/Grafana · Metabase · DataHub

## Cómo levantar el proyecto

Requisitos: Docker Desktop/Engine + Docker Compose, y acceso a internet para descargar los CSVs públicos.

```bash
cp .env.example .env
docker compose up --build -d
```

| Servicio | URL |
|---|---|
| API (Swagger) | `http://localhost:8000/docs` |
| Dagster | `http://localhost:3002` |
| Metabase | `http://localhost:3001` |
| Grafana | `http://localhost:3000` |
| Prometheus | `http://localhost:9090` |

Credenciales de ejemplo y variables completas en [.env.example](.env.example).

Ejemplo de request al endpoint de forecast:

```bash
curl -H "X-API-Key: <API_KEY_VALUE>" \
  "http://localhost:8000/api/v1/forecast?id_pozo=POZO-001&date_start=2026-01-01&date_end=2026-01-01"
```

Para bajar el stack: `docker compose down`.

## Tests

```bash
pip install -r requirements-dev.txt
ruff check .
pytest -q
```

## Documentación ampliada

La documentación detallada de cada fase, decisiones de arquitectura y runbooks de operación vive en [docs/](docs/):

- [Decisiones de arquitectura (ADRs)](docs/adr/)
- [Modelo de datos](docs/data-model.md)
- [Calidad de datos](docs/quality-checks.md)
- [Feature store](docs/feature-store.md)
- [Entrenamiento del modelo](docs/model-training.md)
- [Serving e inferencia](docs/inference-serving.md)
- [Estrategia de deploy](docs/deployment-strategy.md)
- [Checklist de entrega](docs/delivery-checklist.md)

## Alcance y limitaciones

Implementado: ingesta real, warehouse en capas (Bronze/Silver/Gold/Semantic), orquestación con Dagster, calidad de datos persistida, BI en Metabase, catálogo de metadata en DataHub, feature store offline, training con baseline y promotion gate, tracking/registry en MLflow, serving model-backed con fallback local, logging de predicciones, drift check y CI/CD (API + pipeline de ML).

No implementado (fuera de alcance de un TP): alta disponibilidad, autoscaling, Kubernetes, forecast recursivo a futuro, CDC real desde las fuentes públicas, multiambiente dev/staging/prod, y gobierno de datos enterprise (DataHub se usa como catálogo de referencia, no como plataforma productiva con SSO/RBAC/HA).

## Flujo de trabajo

GitFlow simplificado: `feature/* -> develop -> main`, integración por Pull Request, CI en verde antes de mergear. Ver [CONTRIBUTING.md](CONTRIBUTING.md).
