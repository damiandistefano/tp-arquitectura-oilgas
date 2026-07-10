# Checklist de entrega - Trabajo integrador (Fase 1 + Adenda 2 + Adenda 3)

Este documento es la verdad operativa para cerrar la entrega completa: Fase 1 (API, Docker, CI/CD, monitoreo), Fase 2 / Adenda 2 (plataforma de datos) y Fase 3 / Adenda 3 (ML Engineering). Si un componente no puede mostrarse o validarse, se deja aclarado como limitacion y no se promete como productivo.

La validacion obligatoria y reproducible es local con Docker Compose. El sandbox AWS es opcional y complementario: suma evidencia pero no bloquea la entrega.

Responsables por area:

- I1: ingesta, Bronze, metadata, Dagster, estrategia de carga/backfill, feature store, training y retraining.
- I2: dbt, Silver, Gold, Semantic, calidad persistida, Metabase, serving predictivo y prediction logs.
- I3: governance/DataHub, MLflow, CI ML, drift, README, ADR review, runbooks, checklist final y evidencia de entrega.

---

## 1. Estado por componente

| Componente | Responsable | Estado para entrega | Evidencia esperada |
|---|---|---|---|
| API REST + Swagger | Equipo / Fase 1 | Listo | `/health`, `/docs`, endpoints con API key |
| Monitoreo tecnico | Equipo / Fase 1 | Listo | Grafana, Prometheus targets, Alertmanager |
| PostgreSQL warehouse | I1 | Listo | Schemas `bronze`, `silver`, `gold`, `quality`, `metadata`, `semantic` |
| Ingesta Bronze | I1 | Listo | Tablas `bronze.raw_*` con filas y metadata |
| Dagster | I1 | Validado localmente | UI `:3002`, assets visibles, corrida del pipeline o logs |
| dbt Silver/Gold/Semantic | I2 | Listo | `dbt build`, tablas/vistas con filas, dbt Docs |
| Calidad persistida | I2 | Listo | `quality.data_quality_results` con resultados recientes |
| Metabase | I2 | Listo con setup manual | Dashboard `Oil & Gas BI Dashboard`, 6 tarjetas con datos |
| DataHub / governance | I3 | Stack externo en EC2 dedicada | UI `:9002`, datasets del warehouse, columnas/tipos y metadata tecnica |
| Documentacion | I3 + equipo | Lista para entrega | README, ADRs, runbooks, contratos y checklist coherentes |

### Adenda 3 - ML Engineering

| Componente | Responsable | Estado para entrega | Evidencia esperada |
|---|---|---|---|
| Feature store offline | I1 | Listo local | `features.pozo_monthly_features` con grano `id_pozo + periodo_mes` |
| No-leakage temporal | I1 | Cubierto por tests | `pytest tests/test_ml_features.py -q` |
| Training + baseline + promotion gate | I1 | Listo | `ml.train`, baseline `prod_pet_lag_1`, gate con `promoted=true` en fixture |
| Retraining Dagster | I1 | Listo local | Job `ml_training_job` y schedule `ml_retraining_monthly` |
| MLflow tracking + registry + alias | I3 | Listo local | Run en experimento `oilgas_forecaster`, modelo registrado y alias `champion` |
| API forecast model-backed | I2 | Listo local | `/api/v1/forecast` responde 200 con `model.source = mlflow` |
| Prediction logs | I2 | Listo | Filas en `metadata.prediction_logs` con `status`, `model_source`, latencia y metadata |
| Drift check | I3 | Listo | `bash scripts/run-drift-check.sh 2026-01-01` emite JSON con `drifted` por feature |
| ML CI | I3 | Listo | Workflow `.github/workflows/ml-ci.yml` y `scripts/data-ml-ci-smoke.sh` |
| Validacion final | I3 | Lista | `bash scripts/validate-delivery.sh` |

Nota sobre DataHub: no aparece en el `docker-compose.yml` principal porque su quickstart es pesado. Se opera con una EC2 dedicada y on-demand; ver [docs/runbooks/datahub.md](runbooks/datahub.md).

---

## 1.1 Instancias e IPs para la demo

La validacion oficial es local. Las instancias AWS son sandbox opcional/evidencia complementaria; si estan apagadas, la entrega se valida igual con el stack local. No commitear llaves `.pem`, `.env` reales ni capturas con secretos.

| Instancia | Uso | URL/IP a validar | Caracter |
|---|---|---|---|
| Stack ML local (obligatorio) | Postgres, MLflow, API, Dagster | `http://localhost:5000` (MLflow), `http://localhost:8000` (API), `http://localhost:3002` (Dagster) | Validacion local reproducible |
| Stack de datos (obligatorio) | Postgres, Dagster, Metabase, dbt | `http://localhost:3002` (Dagster) y `http://localhost:3001` (Metabase), con `docker compose up` | Validacion local reproducible |
| Sandbox API/monitoreo | API, Swagger, Prometheus, Grafana, Alertmanager, cAdvisor | `http://18.118.45.3` (`:8000` `:3000` `:9090` `:9093`) | AWS opcional |
| DataHub | Catalogo/governance | `http://18.118.110.246:9002` | AWS opcional |

Dagster y Metabase no se exponen en el sandbox: se levantan localmente con `docker compose up`. El profe puede correrlos en su maquina con las instrucciones del README, o verlos en la demo en vivo.

---

## 2. Arranque desde cero

### Pre-requisitos

- Docker Desktop o Docker Engine + Docker Compose.
- Python 3 con `pip`, o entorno equivalente usado por el equipo.
- Acceso a internet para descargar CSVs desde datos.energia.gob.ar.

### 1. Configurar entorno

```bash
cp .env.example .env
```

Revisar puertos segun desde donde se ejecute:

- Desde la maquina host: Postgres se accede por `localhost:5433`.
- Desde contenedores en Compose: Postgres se accede por `postgres:5432`.

### 2. Levantar stack

```bash
docker compose up --build -d
docker compose ps
```

Servicios esperados:

- `postgres` / `warehouse-postgres` healthy.
- `api` en `8000`.
- `prometheus` en `9090`.
- `grafana` en `3000`.
- `alertmanager` en `9093`.
- `cadvisor` en `8080`.
- `metabase` en `3001`.
- `dagster` en `3002`.

### 3. Ejecutar pipeline de datos

Opcion A: desde Dagster UI.

1. Abrir `http://localhost:3002`.
2. Ver assets `extract_to_bronze`, `run_silver_transformations`, `run_quality_checks`.
3. Materializar el pipeline.
4. Revisar logs por asset.

Opcion B: comandos manuales.

```bash
python -m extract.load_to_bronze

cd dbt
dbt debug
dbt build
dbt docs generate
cd ..

python -m quality.checks
```

---

## 3. Verificaciones automaticas y semi-automaticas

### Codigo y configuracion

```bash
ruff check .
pytest -q
docker compose config
IMAGE_TAG=ci API_PORT=8002 docker compose -f docker-compose.deploy.yml config
```

### API y monitoreo

```bash
curl http://localhost:8000/health
curl http://localhost:8000/openapi.json
curl -H "X-API-Key: abcdef12345" "http://localhost:8000/api/v1/wells?date_query=2026-03-15"
curl http://localhost:3000/api/health
curl http://localhost:9090/-/healthy
```

### Warehouse

```bash
psql -h localhost -p 5433 -U dwh -d warehouse -c "
  SELECT 'bronze.raw_produccion_no_convencional' AS tabla, count(*) FROM bronze.raw_produccion_no_convencional
  UNION ALL
  SELECT 'bronze.raw_pozos', count(*) FROM bronze.raw_pozos_operadoras
  UNION ALL
  SELECT 'silver.produccion', count(*) FROM silver.produccion_no_convencional
  UNION ALL
  SELECT 'gold.fact_produccion_pozo', count(*) FROM gold.fact_produccion_pozo
  UNION ALL
  SELECT 'semantic.vw_produccion_mensual', count(*) FROM semantic.vw_produccion_mensual;
"
```

### Calidad

```bash
psql -h localhost -p 5433 -U dwh -d warehouse -c "
  SELECT check_name, layer, table_name, status, severity, executed_at
  FROM quality.data_quality_results
  ORDER BY executed_at DESC
  LIMIT 20;
"
```

### Metabase

Entrar a `http://localhost:3001` y validar:

- login `martinbianchi@udesa.edu.ar` / `Admin1234!`;
- conexion a PostgreSQL `postgres:5432`;
- base `warehouse`;
- dashboard `Oil & Gas BI Dashboard`;
- tarjetas con datos sobre `semantic.*` y `quality.data_quality_results`;
- evidencia de validacion.

### Dagster

Entrar a `http://localhost:3002` y validar:

- assets visibles;
- grafo de dependencias;
- corrida exitosa o, si falla, logs claros;
- evidencia de validacion.

### dbt Docs

```bash
cd dbt
dbt docs generate
dbt docs serve
```

Validar modelos, columnas, tests y lineage.

### Adenda 3 local

Primera corrida despues del cambio de MLflow:

```bash
docker compose down -v
cp .env.example .env
mkdir -p ml_artifacts
docker compose up --build -d postgres mlflow api dagster
set -a; . ./.env; set +a
bash scripts/mlflow-smoke.sh
bash scripts/data-ml-ci-smoke.sh
```

Evidencia minima:

- training registra un run en MLflow y una version de `oilgas_forecaster`;
- gate imprime `promoted: true`;
- alias `champion` queda verificado por el smoke;
- forecast devuelve HTTP 200 y `model.source = mlflow`;
- `metadata.prediction_logs` tiene una fila `success` con `model_source = mlflow`;
- drift check corre y muestra `drifted` por feature.

### DataHub (sandbox AWS opcional)

Validar en la EC2 dedicada antes de grabar o mostrar la demo, solo si se muestra el sandbox:

| Dato | Valor |
|---|---|
| URL cuando esta encendida | `http://18.118.110.246:9002` |
| Como se levanta | EC2 dedicada. Por disco acotado el CLI `datahub docker quickstart` no entra; se levanta el compose cacheado: `cd ~/.datahub/quickstart && COMPOSE_PROFILES=quickstart DATAHUB_VERSION=v1.5.0.6 docker compose -p datahub -f docker-compose.yml --env-file .local-secrets.env up -d --pull never` |
| Credenciales | `datahub` / `datahub` |
| Ingesta | `datahub ingest -c datahub/recipe.postgres.yml` |
| Datasets visibles | `bronze`, `silver`, `gold`, `quality`, `metadata`, `semantic` |
| Evidencia guardada | Capturas o registro de validacion de UI |

Evidencia minima esperada:

- datasets del warehouse visibles;
- columnas y tipos visibles;
- capas medallion navegables;
- detalle de `gold.fact_produccion_pozo`;
- si la UI muestra lineage, incluirlo; si no, apoyar el linaje tecnico con dbt Docs y Dagster.

---

## 4. Inventario de entregables

### ADRs

Ver indice completo en [docs/adr/README.md](adr/README.md).

| Rango | Estado |
|---|---|
| 0001-0005 | Presentes, Fase 1 |
| 0006-0008 | Presentes, I1: Dagster, carga/backfill, warehouse |
| 0009-0012 | Presentes, I2: Medallion, Gold, calidad, Semantic |
| 0013 | Presente, I3: DataHub / governance |
| 0014 | Presente, I2: Metabase / BI |
| 0015-0023 | Presentes, Adenda 3: forecasting, MLflow, feature store, gate, retraining, serving, ML CI, prediction logs y drift |

### Runbooks

| Archivo | Estado |
|---|---|
| `docs/runbooks/local-stack.md` | Presente |
| `docs/runbooks/deploy-aws.md` | Presente |
| `docs/runbooks/sandbox-validation.md` | Presente |
| `docs/runbooks/bi-user.md` | Presente |
| `docs/runbooks/dbt-analytics.md` | Presente |
| `docs/runbooks/data-engineer.md` | Presente |
| `docs/runbooks/datahub.md` | Presente |

### Datos y calidad

| Archivo | Estado |
|---|---|
| `docs/data-contracts-2.md` | Presente |
| `docs/data-model.md` | Presente |
| `docs/quality-checks.md` | Presente |

### ML Engineering

| Archivo | Estado |
|---|---|
| `docs/feature-store.md` | Presente |
| `docs/model-training.md` | Presente |
| `docs/inference-serving.md` | Presente |

---

## 5. Checklist final de entrega

### Validacion local obligatoria (reproducible)

#### Fase 1 - stack base

- [ ] `docker compose up --build -d` levanta sin errores.
- [ ] Postgres queda healthy.
- [ ] API responde `/health`.
- [ ] Grafana abre en `:3000`.
- [ ] Prometheus abre en `:9090`.
- [ ] Dagster abre en `:3002`.
- [ ] Metabase abre en `:3001`.
- [ ] `ruff check .`, `pytest -q` y `docker compose config` pasan.

#### Fase 2 - pipeline de datos

- [ ] Bronze tiene filas.
- [ ] dbt construye Silver/Gold/Semantic.
- [ ] Quality checks se persisten y no hay `FAILED` criticos sin explicar.
- [ ] Dagster muestra corrida o logs de la orquestacion.
- [ ] Metabase muestra dashboard con datos.
- [ ] dbt Docs muestra lineage.

#### Fase 3 / Adenda 3 - ML Engineering

- [ ] `docker compose down -v` ejecutado al menos una vez despues del cambio de MLflow.
- [ ] Feature store poblado: `features.pozo_monthly_features` con grano `id_pozo + periodo_mes`.
- [ ] No-leakage verificado: `pytest tests/test_ml_features.py -q` pasa.
- [ ] Training corre: `python -m ml.train` registra run y artefactos.
- [ ] Baseline `prod_pet_lag_1` evaluado sobre las mismas filas de test que el modelo.
- [ ] Promotion gate decide: primer modelo se promueve; un candidato que no mejora no mueve el alias.
- [ ] Retraining con Dagster: job `ml_training_job` repetible para un dia dado y schedule `ml_retraining_monthly` visibles.
- [ ] MLflow tracking muestra runs con parametros y metricas comparables.
- [ ] Model Registry tiene el modelo `oilgas_forecaster` versionado.
- [ ] Alias `champion` apunta a la version promovida.
- [ ] `bash scripts/mlflow-smoke.sh` pasa.
- [ ] `bash scripts/data-ml-ci-smoke.sh` pasa completo (requiere stack limpio).
- [ ] `/api/v1/forecast` devuelve 200 con `model.source = mlflow`.
- [ ] `metadata.prediction_logs` registra filas `success` y `error` con `model_source`.
- [ ] `bash scripts/run-drift-check.sh 2026-01-01` corre y reporta `drifted` por feature.
- [ ] ML CI (`ml-ci.yml`) en verde, incluida la validacion de Dagster (`ml_training_job` + `ml_retraining_monthly`).
- [ ] `bash scripts/validate-delivery.sh` pasa (baja volumenes al final: no correrlo en medio de una demo).

#### Documentacion

- [ ] README refleja el estado real y tiene la seccion "Arquitectura completa de la solucion".
- [ ] ADRs tienen alternativas y trade-offs; el indice cubre Adenda 3.
- [ ] Runbooks tienen pasos, validacion y que hacer si falla.
- [ ] No quedan TODOs ni frases de borrador; las URLs variables de entrega estan identificadas como sandbox opcional.
- [ ] No se promete produccion real ni alta disponibilidad.

### Sandbox AWS opcional (complementario)

- [ ] Imagen GHCR publicada para el commit final si se usa deploy desde registry.
- [ ] Smoke test de AWS ejecutado por script o workflow manual si se muestra EC2.
- [ ] DataHub abre en `:9002` y muestra datasets del warehouse si se muestra la EC2 dedicada.

### Cierre de entrega

- [ ] Video de Adenda 3 grabado (5-10 min): arquitectura, herramientas, rationale, runs comparables en MLflow, retraining, gate que promueve y gate que rechaza, forecast 200 `source = mlflow`, prediction logs y drift.
- [ ] `develop` tiene todos los merges y CI en verde.
- [ ] PR `develop -> main` abierto, revisado y mergeado.
- [ ] Tag de release `v0.3.0` creado en `main` (v0.1.0 y v0.2.0 ya existen de fases anteriores).
- [ ] Zip armado sin `.env`, `.pem`, caches, dumps, outputs generados ni `/contexto`.
- [ ] Zip revisado contra la lista de exclusiones.
