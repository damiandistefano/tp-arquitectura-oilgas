# tp-arquitectura-oilgas

Trabajo integrador de Ingenieria de Software para un sistema predictivo de produccion de hidrocarburos.

El repo presenta una plataforma integral construida en tres fases:

- Fase 1: API REST FastAPI, Docker, CI/CD, GHCR, despliegue sandbox y monitoreo tecnico.
- Fase 2 / Adenda 2: plataforma de datos con warehouse PostgreSQL, arquitectura Medallion, Dagster, dbt, calidad persistida, capa semantic, BI en Metabase y gobierno de datos con DataHub.
- Fase 3 / Adenda 3: ML Engineering con feature store offline, training batch, baseline, promotion gate, MLflow (tracking + registry), model serving, prediction logs, drift check y CI de ML.

La entrega sigue siendo un sandbox academico. No se presenta como una plataforma productiva con alta disponibilidad, gobierno enterprise o despliegue multiambiente completo.

---

## Arquitectura completa de la solucion

Las tres fases forman un unico flujo, de datos publicos a forecast servido por API:

```text
datos publicos (datos.gob.ar)
  -> Bronze (ingesta append-only con hash de archivo)
  -> Silver (limpieza y tipado con dbt)
  -> Gold (modelo estrella: fact_produccion_pozo + dimensiones)
  -> Semantic (vistas SQL para BI)
  -> Feature Store (features.pozo_monthly_features)
  -> Training / Validation (ml.train + baseline naive + split temporal)
  -> MLflow Tracking + Model Registry (modelo oilgas_forecaster)
  -> Promotion Gate (ml.promotion_gate mueve el alias champion solo si mejora)
  -> FastAPI Forecast (GET /api/v1/forecast)
  -> Prediction Logs (metadata.prediction_logs)
  -> Drift Check (ml.drift_check)
  -> CI/CD (GitHub Actions: ci.yml + ml-ci.yml)
```

### Cobertura de requerimientos

| Requerimiento | Herramienta / implementacion |
|---|---|
| Data Warehouse | PostgreSQL con schemas `bronze`, `silver`, `gold`, `quality`, `metadata`, `semantic` y `features` |
| Pre-proc / generacion de features | `ml.build_features` puebla `features.pozo_monthly_features` desde Gold |
| Feature Store | Schema `features` en Postgres, persistido y consumido por training y por la inferencia |
| Training | `ml.train` (HistGradientBoosting, baseline `prod_pet_lag_1`, split temporal sin leakage) |
| Validation / gate | `ml.promotion_gate` compara candidato contra baseline y champion |
| Orquestacion | Dagster: `ml_training_job` repetible para un dia dado y schedule `ml_retraining_monthly` |
| Experiment Tracking | MLflow (runs con parametros, metricas y artefactos) |
| Model Registry | MLflow Model Registry, modelo `oilgas_forecaster` con alias `champion` |
| API REST | FastAPI `GET /api/v1/forecast` con feature enrichment y metadata runtime |
| Logs de inferencia | `metadata.prediction_logs` en Postgres |
| Drift | `ml.drift_check` + `scripts/run-drift-check.sh`, z-score por feature |
| CI/CD | GitHub Actions: `ci.yml` (API, imagen, stack) + `ml-ci.yml` (pipeline ML con fixture) |

### Alcance de la evaluacion

- La evaluacion reproducible es local con Docker Compose (`docker-compose.yml`).
- El sandbox AWS es opcional y complementario: evidencia de deploy de Fase 1 y de DataHub, no camino oficial de correccion.
- La demo ML model-backed de Adenda 3 se valida localmente y no depende de IPs publicas prendidas.
- No se promete produccion real: sin alta disponibilidad, autoscaling, forecast recursivo ni Adenda 3 en AWS.

---

## Sandbox AWS opcional (evidencia complementaria)

El camino oficial y reproducible de la entrega es el stack local con Docker Compose (ver secciones siguientes). Las instancias AWS son un sandbox opcional que complementa la evidencia de Fase 1 (deploy de API + monitoreo desde GHCR) y de gobierno de datos (DataHub). Pueden estar apagadas sin afectar la validacion de Adenda 3.

IPs del sandbox cuando esta encendido:

- Sandbox API + monitoreo: `18.118.45.3`
- DataHub (gobierno de datos): `18.118.110.246`

Metabase y Dagster no se exponen en el sandbox: se levantan localmente con `docker compose up` (ver mas abajo).

### Fase 1 (sandbox opcional)

| Servicio | URL | Credenciales / notas |
|---|---|---|
| API | `http://18.118.45.3:8000` | - |
| Swagger / OpenAPI UI | `http://18.118.45.3:8000/docs` | Header `X-API-Key: abcdef12345` para endpoints funcionales |
| OpenAPI JSON | `http://18.118.45.3:8000/openapi.json` | - |
| Grafana | `http://18.118.45.3:3000` | `admin` / `pKNF9UsS4mzDtnA` |
| Prometheus | `http://18.118.45.3:9090` | - |
| Alertmanager | `http://18.118.45.3:9093` | Slack real solo si se configura webhook valido |

### Fase 2 (stack local + DataHub opcional)

| Servicio | URL | Estado de entrega |
|---|---|---|
| PostgreSQL warehouse | `localhost:5433` desde host / `postgres:5432` desde contenedores | Implementado en `docker-compose.yml` |
| Dagster | `http://localhost:3002` (local) | Orquestador del pipeline de datos y del retraining ML (`dagster/dwh_pipeline/`). Se levanta localmente con `docker compose up`; no expuesto en el sandbox |
| Metabase | `http://localhost:3001` (local) | BI sobre vistas `semantic.*`; usuario `martinbianchi@udesa.edu.ar` / `Admin1234!`. Se levanta localmente con `docker compose up`; no expuesto en el sandbox |
| dbt Docs | local, generado con `dbt docs generate` | Evidencia de modelos, tests y lineage de dbt |
| DataHub | `http://18.118.110.246:9002` (opcional) | Catalogo de metadata del warehouse en EC2 dedicada; usuario `datahub` / `datahub` |

DataHub no aparece en el `docker-compose.yml` principal de este repo porque su quickstart es pesado. Se opera como stack externo en una EC2 dedicada y on-demand. Ver [docs/runbooks/datahub.md](docs/runbooks/datahub.md).

---

## Arquitectura de Fase 2

El pipeline de datos usa fuentes publicas de datos.gob.ar y procesa la informacion por capas:

```text
datos.gob.ar
  -> bronze.raw_*
  -> silver.*
  -> gold.fact_produccion_pozo + dimensiones
  -> quality.data_quality_results
  -> semantic.vw_*
  -> Metabase / dbt Docs / DataHub
```

### Componentes principales

| Componente | Que hace |
|---|---|
| PostgreSQL | Warehouse local/sandbox con schemas `bronze`, `silver`, `gold`, `quality`, `metadata` y `semantic`. |
| Dagster | Orquesta ingesta, transformaciones dbt y checks de calidad como assets. |
| extract/ | Descarga CSVs publicos, calcula hash y carga Bronze con metadata de corrida. |
| dbt | Construye modelos Silver, Gold y vistas Semantic. |
| quality/ | Ejecuta checks y persiste resultados en `quality.data_quality_results`. |
| Metabase | Dashboard de negocio para usuarios no tecnicos. |
| DataHub | Catalogo de metadata del warehouse, desplegado por fuera del Compose principal. |
| Prometheus/Grafana/Alertmanager | Monitoreo tecnico de la API y servicios del stack. |

### Fuentes de datos

- Produccion de pozos de gas y petroleo no convencional.
- Listado de pozos cargados por empresas operadoras.

Las URLs estan en `.env.example` y `.env.sandbox.example`.

### Estrategia de carga

La carga es batch. Se descarga el CSV completo, se calcula hash de archivo y Bronze se mantiene append-only por corrida. Si el mismo hash ya fue cargado, la ingesta evita duplicar esa fuente.

Esta decision esta documentada en [ADR 0007](docs/adr/0007-definir-estrategia-de-carga-y-backfill.md). No se implementa CDC real porque la fuente publica no expone un mecanismo incremental confiable.

### Modelo Gold

La fact table principal es `gold.fact_produccion_pozo`.

Grano:

- una fila por registro de produccion de un pozo en un periodo mensual.

Dimensiones:

- `gold.dim_fecha`
- `gold.dim_pozo`
- `gold.dim_operadora`
- `gold.dim_area`
- `gold.dim_yacimiento`

Ver [docs/data-model.md](docs/data-model.md).

### Calidad de datos

Los checks quedan persistidos en `quality.data_quality_results`.

Dimensiones cubiertas:

- schema;
- completeness;
- uniqueness;
- lineage / relationships;
- freshness.

Si falla un check `CRITICAL`, el comando de calidad termina con exit code distinto de cero. Los warnings quedan registrados para revision sin bloquear necesariamente la ejecucion.

Ver [docs/quality-checks.md](docs/quality-checks.md).

### BI y capa semantic

Metabase consume vistas del schema `semantic`, no Bronze. Las vistas principales son:

- `semantic.vw_produccion_mensual`
- `semantic.vw_produccion_por_operadora`
- `semantic.vw_produccion_por_area`
- `semantic.vw_frescura_datos`

El dashboard de BI se llama `Oil & Gas BI Dashboard`. Las tarjetas y consultas esperadas estan documentadas en [docs/runbooks/bi-user.md](docs/runbooks/bi-user.md).

---

## Como levantar el stack local

Requisitos:

- Docker Desktop o Docker Engine.
- Docker Compose.
- Python 3 y dependencias del proyecto si se ejecutan comandos fuera de contenedores.
- Acceso a internet para descargar los CSVs publicos.

Desde la raiz del repo:

```bash
cp .env.example .env
docker compose up --build -d
```

Servicios locales:

| URL | Que es | Credenciales / notas |
|---|---|---|
| `http://localhost:8000/docs` | Swagger de la API | Header `X-API-Key: abcdef12345` |
| `http://localhost:8000/metrics` | Metric endpoint | - |
| `http://localhost:9090` | Prometheus | - |
| `http://localhost:3000` | Grafana | `admin` / `pKNF9UsS4mzDtnA` |
| `http://localhost:9093` | Alertmanager | - |
| `http://localhost:8080` | cAdvisor | - |
| `http://localhost:3001` | Metabase | `martinbianchi@udesa.edu.ar` / `Admin1234!` |
| `http://localhost:3002` | Dagster | UI de assets del pipeline |

Para bajar el stack:

```bash
docker compose down
```

---

## Demo Adenda 3 (local)

La demo model-backed de Adenda 3 se valida localmente con el Compose completo.
La primera vez despues del cambio de MLflow hay que resetear volumenes para que
el experimento use `mlflow-artifacts:/` y el tracking server proxy artifacts por HTTP.

```bash
docker compose down -v
cp .env.example .env
mkdir -p ml_artifacts
docker compose up --build -d postgres mlflow api dagster

set -a; . ./.env; set +a
bash scripts/mlflow-smoke.sh
bash scripts/data-ml-ci-smoke.sh
```

El smoke integrado carga el fixture, genera features, entrena, registra el modelo
en MLflow, ejecuta el promotion gate, verifica alias `champion`, llama a la API
con `REQUIRE_200=1` y `EXPECTED_MODEL_SOURCE=mlflow`, valida prediction logs y
corre drift check.

Curl final de demo:

```bash
curl -s -H "X-API-Key: abcdef12345" \
  "http://localhost:8000/api/v1/forecast?id_pozo=POZO-001&date_start=2026-01-01&date_end=2026-01-01" | jq
```

El rango debe existir en `features.pozo_monthly_features`. Con el fixture de ML CI
el ultimo mes disponible es `2026-01-01`; usar meses futuros no generados devuelve
404 controlado.

Prediction logs:

```bash
docker compose exec -T postgres psql -U dwh -d warehouse -c \
  "select prediction_id, requested_at, id_pozo, status, model_name, model_version, mlflow_run_id, model_source, latency_ms
   from metadata.prediction_logs order by requested_at desc limit 5;"
```

Drift check:

```bash
bash scripts/run-drift-check.sh 2026-01-01
```

Dagster expone el job `ml_training_job` y el schedule `ml_retraining_monthly` en
`http://localhost:3002`.

---

## Ejecucion del pipeline de datos

### Opcion 1: Dagster UI

1. Levantar el stack con `docker compose up --build -d`.
2. Entrar a `http://localhost:3002`.
3. Materializar los assets:
   - `extract_to_bronze`
   - `run_silver_transformations`
   - `run_quality_checks`
4. Revisar logs y estado de cada asset.

### Opcion 2: comandos manuales

Cargar Bronze:

```bash
python -m extract.load_to_bronze
```

Construir modelos dbt:

```bash
cd dbt
dbt debug
dbt build
dbt docs generate
cd ..
```

Ejecutar quality gate:

```bash
python -m quality.checks
```

Validar BI:

```bash
bash scripts/metabase-smoke.sh
```

En Windows, los scripts Bash requieren Git Bash, WSL o un entorno compatible. Si se ejecuta desde PowerShell, setear variables con `$env:NOMBRE='valor'`.

---

## API y forecast predictivo

Todos los endpoints funcionales requieren:

```http
X-API-Key: abcdef12345
```

Endpoints principales:

| Metodo | Endpoint | Descripcion |
|---|---|---|
| `GET` | `/api/v1/wells?date_query=YYYY-MM-DD` | Devuelve pozos activos para la fecha consultada. |
| `GET` | `/api/v1/forecast?id_pozo=POZO-001&date_start=YYYY-MM-DD&date_end=YYYY-MM-DD` | Devuelve forecast mensual model-backed para el pozo y rango indicado. |
| `GET` | `/health` | Health check del servicio. |
| `GET` | `/metrics` | Metricas Prometheus. |
| `GET` | `/docs` | Swagger/OpenAPI. |

`/api/v1/wells` conserva el contrato legacy de Fase 1 con `id_well`. El contrato
vigente de Adenda 3 para inferencia es `/api/v1/forecast` con `id_pozo`.

Ejemplos:

```bash
curl -H "X-API-Key: abcdef12345" \
  "http://localhost:8000/api/v1/wells?date_query=2026-03-15"

curl -H "X-API-Key: abcdef12345" \
  "http://localhost:8000/api/v1/forecast?id_pozo=POZO-001&date_start=2026-01-01&date_end=2026-01-01"
```

El forecast usa features de `features.pozo_monthly_features`, carga el modelo
activo `oilgas_forecaster` alias `champion` via adapter y devuelve metadata
runtime (`version`, `run_id`, `source`). Si MLflow no esta disponible, puede
usar fallback local visible con `model.source = local_fallback`.

La imagen de API instala las dependencias minimas para servir artifacts sklearn
locales (`pandas`, `scikit-learn`, `joblib`) y monta `ml_artifacts` como solo
lectura en Compose.

Cada request con fechas validas intenta persistir metadata de inferencia en
`metadata.prediction_logs`. Ver [docs/inference-serving.md](docs/inference-serving.md).

---

## Tests y validaciones

Instalar dependencias de desarrollo:

```bash
pip install -r requirements-dev.txt
```

Correr analisis estatico y tests:

```bash
ruff check .
pytest -q
```

Validar Compose:

```bash
docker compose config
IMAGE_TAG=ci API_PORT=8002 docker compose -f docker-compose.deploy.yml config
bash scripts/validate-delivery.sh
```

Validaciones manuales recomendadas antes de entregar:

- Dagster abre en `:3002`, muestra assets y una corrida exitosa.
- Metabase abre en `:3001`, conectado al warehouse, con dashboard y tarjetas con datos.
- dbt Docs genera y muestra lineage/modelos/tests.
- `quality.data_quality_results` tiene resultados recientes.
- GitHub Actions esta verde en el commit final.
- GHCR tiene la imagen esperada si se usa deploy desde registry.
- El workflow manual `AWS Smoke Test` o `scripts/sandbox-smoke.sh` valida la EC2 si se muestra el sandbox.
- El workflow `ml-ci.yml` valida el fixture chico de ML con Postgres, MLflow, API y drift check, y que el repo Dagster carga con `ml_training_job` y `ml_retraining_monthly`.
- DataHub muestra datasets del warehouse y metadata tecnica en la EC2 dedicada.

Ver [docs/delivery-checklist.md](docs/delivery-checklist.md).

---

## CI/CD

Los workflows `ci.yml` y `ml-ci.yml` corren en cada pull request hacia `develop` y `main`, y en push a `main`, `develop` y `feature/**`.

GitHub Actions ejecuta validaciones de Fase 1 y controles generales:

- instalacion de dependencias;
- Ruff;
- Pytest;
- validacion de OpenAPI;
- contrato de endpoints protegidos;
- build de imagen Docker;
- Trivy;
- smoke test de contenedor;
- validacion de scripts;
- validacion de Compose;
- chequeo de archivos sensibles;
- smoke test del stack tecnico;
- validacion de metricas, targets y reglas de Prometheus.

En `main`, el pipeline publica imagen de la API en GHCR con tags:

- `latest`;
- commit SHA.

Los checks de datos completos requieren warehouse y fuentes externas, por eso tambien se validan manualmente con el checklist de entrega.

Para validar una EC2 ya desplegada desde GitHub, existe el workflow manual `AWS Smoke Test`. Recibe la base URL publica y revisa API, metricas, endpoints protegidos, Grafana, Prometheus y Alertmanager.

---

## Deploy a EC2 sandbox

La estrategia de deploy esta documentada en:

- [docs/deployment-strategy.md](docs/deployment-strategy.md)
- [docs/runbooks/deploy-aws.md](docs/runbooks/deploy-aws.md)
- [docs/runbooks/sandbox-validation.md](docs/runbooks/sandbox-validation.md)

Deploy:

```bash
IMAGE_TAG=<commit_sha> ./scripts/deploy.sh
```

Rollback:

```bash
./scripts/rollback.sh <commit_sha_anterior>
```

Smoke test del sandbox:

```bash
bash scripts/sandbox-smoke.sh 18.118.45.3
```

`docker-compose.deploy.yml` no incluye Postgres ni MLflow. Por eso el forecast
model-backed de Adenda 3 no se valida en la EC2: el sandbox AWS valida API y
monitoreo de Fase 1; la demo ML se valida local con `docker-compose.yml`.

---

## Decisiones de arquitectura

Las decisiones estan en [docs/adr/](docs/adr/).

Fase 1:

- Docker Compose para stack local.
- GitHub Actions para CI.
- GHCR para imagenes.
- Prometheus, Grafana, Alertmanager y cAdvisor.
- Trivy para escaneo de vulnerabilidades.

Fase 2:

- Dagster como orquestador.
- Full download + Bronze append-only con hash.
- PostgreSQL como warehouse local/sandbox.
- Arquitectura Medallion.
- Modelo estrella en Gold.
- Calidad persistida.
- Vistas SQL como semantic layer.
- DataHub como catalogo de gobierno de datos.

Adenda 3:

- MLflow para tracking, registry y alias `champion`.
- Postgres como feature store offline.
- Baseline naive y promotion gate.
- Serving model-backed por `/api/v1/forecast`.
- Prediction logs y drift check minimo.

---

## Alcance y limitaciones

Implementado:

- API REST con forecast mensual model-backed.
- Dockerizacion.
- CI/CD y GHCR para API.
- Monitoreo tecnico.
- Ingesta real desde datos.gob.ar.
- Bronze/Silver/Gold/Semantic.
- Dagster para orquestacion.
- Quality checks persistidos.
- Metabase para BI.
- DataHub como catalogo externo de metadata.
- Feature store offline, training batch y serving predictivo con adapter.
- MLflow local para tracking, registry y alias `champion`.
- ML CI con fixture chico y smoke end-to-end.
- ADRs, runbooks y checklist de entrega.

Limitaciones asumidas:

- El serving es de alcance sandbox academico: no hay alta disponibilidad,
  canary releases ni plataforma enterprise de modelos.
- El forecast model-backed de Adenda 3 se valida localmente; el compose de deploy
  AWS no incluye Postgres ni MLflow.
- El forecast mensual opera sobre periodos existentes en el feature store; no se
  implementa generacion recursiva de meses futuros.
- No hay CDC real desde las fuentes publicas.
- No hay alta disponibilidad ni Kubernetes.
- No hay multiambiente completo dev/staging/prod.
- No hay gobierno enterprise: DataHub se usa como catalogo academico, no como plataforma productiva con SSO/RBAC/HA.
- Dashboard de Metabase se configura desde UI, no se provisiona automaticamente como codigo.

---

## Flujo de trabajo

El repo usa GitFlow simplificado:

```text
feature/* -> develop -> main
```

Reglas:

- no commitear directo a `main`;
- integrar por Pull Request;
- mantener CI en verde;
- actualizar documentacion junto con cambios de comportamiento;
- no commitear `.env`, `.pem`, tokens, claves privadas, dumps, caches ni outputs generados.

Ver [CONTRIBUTING.md](CONTRIBUTING.md).
