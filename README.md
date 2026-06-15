# tp-arquitectura-oilgas

Trabajo integrador de Ingenieria de Software para un sistema predictivo de produccion de hidrocarburos.

El repo cubre dos etapas:

- Fase 1: API REST mock, Docker, CI/CD, GHCR, despliegue sandbox y monitoreo tecnico.
- Fase 2: integracion de datos con arquitectura Medallion, warehouse PostgreSQL, Dagster, dbt, calidad persistida, capa semantic, BI en Metabase y gobierno de datos con DataHub.

La entrega sigue siendo un sandbox academico. No se presenta como una plataforma productiva con alta disponibilidad, gobierno enterprise o despliegue multiambiente completo.

---

## URLs oficiales de entrega

IPs vigentes de la entrega (instancias activas durante la correccion):

- Sandbox API + monitoreo: `16.59.211.99`
- DataHub (gobierno de datos): `3.143.210.125`

Metabase y Dagster no se exponen en el sandbox: se levantan localmente con `docker compose up` (ver mas abajo). El resto de las URLs son publicas.

### Fase 1

| Servicio | URL | Credenciales / notas |
|---|---|---|
| API | `http://16.59.211.99:8000` | - |
| Swagger / OpenAPI UI | `http://16.59.211.99:8000/docs` | Header `X-API-Key: abcdef12345` para endpoints funcionales |
| OpenAPI JSON | `http://16.59.211.99:8000/openapi.json` | - |
| Grafana | `http://16.59.211.99:3000` | `admin` / `admin` |
| Prometheus | `http://16.59.211.99:9090` | - |
| Alertmanager | `http://16.59.211.99:9093` | Slack real solo si se configura webhook valido |

### Fase 2

| Servicio | URL | Estado de entrega |
|---|---|---|
| PostgreSQL warehouse | `localhost:5433` desde host / `postgres:5432` desde contenedores | Implementado en `docker-compose.yml` |
| Dagster | `http://localhost:3002` (local) | Orquestador del pipeline de datos (`dagster/dwh_pipeline/`). Se levanta localmente con `docker compose up`; no expuesto en el sandbox |
| Metabase | `http://localhost:3001` (local) | BI sobre vistas `semantic.*`; usuario `martinbianchi@udesa.edu.ar` / `Admin1234!`. Se levanta localmente con `docker compose up`; no expuesto en el sandbox |
| dbt Docs | local, generado con `dbt docs generate` | Evidencia de modelos, tests y lineage de dbt |
| DataHub | `http://3.143.210.125:9002` | Catalogo de metadata del warehouse en EC2 dedicada; usuario `datahub` / `datahub` |

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
| `http://localhost:3000` | Grafana | `admin` / `admin` |
| `http://localhost:9093` | Alertmanager | - |
| `http://localhost:8080` | cAdvisor | - |
| `http://localhost:3001` | Metabase | `martinbianchi@udesa.edu.ar` / `Admin1234!` |
| `http://localhost:3002` | Dagster | UI de assets del pipeline |

Para bajar el stack:

```bash
docker compose down
```

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

## API mock de Fase 1

Todos los endpoints funcionales requieren:

```http
X-API-Key: abcdef12345
```

Endpoints principales:

| Metodo | Endpoint | Descripcion |
|---|---|---|
| `GET` | `/api/v1/wells?date_query=YYYY-MM-DD` | Devuelve pozos activos para la fecha consultada. |
| `GET` | `/api/v1/forecast?id_well=POZO-001&date_start=YYYY-MM-DD&date_end=YYYY-MM-DD` | Devuelve un pronostico mock diario para el pozo y rango indicado. |
| `GET` | `/health` | Health check del servicio. |
| `GET` | `/metrics` | Metricas Prometheus. |
| `GET` | `/docs` | Swagger/OpenAPI. |

Ejemplos:

```bash
curl -H "X-API-Key: abcdef12345" \
  "http://localhost:8000/api/v1/wells?date_query=2026-03-15"

curl -H "X-API-Key: abcdef12345" \
  "http://localhost:8000/api/v1/forecast?id_well=POZO-001&date_start=2026-03-15&date_end=2026-03-20"
```

La API usa datos mock deterministas. El modelo predictivo real queda fuera de Fase 1.

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
```

Validaciones manuales recomendadas antes de entregar:

- Dagster abre en `:3002`, muestra assets y una corrida exitosa.
- Metabase abre en `:3001`, conectado al warehouse, con dashboard y tarjetas con datos.
- dbt Docs genera y muestra lineage/modelos/tests.
- `quality.data_quality_results` tiene resultados recientes.
- GitHub Actions esta verde en el commit final.
- GHCR tiene la imagen esperada si se usa deploy desde registry.
- El workflow manual `AWS Smoke Test` o `scripts/sandbox-smoke.sh` valida la EC2 si se muestra el sandbox.
- DataHub muestra datasets del warehouse y metadata tecnica en la EC2 dedicada.

Ver [docs/delivery-checklist.md](docs/delivery-checklist.md).

---

## CI/CD

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
bash scripts/sandbox-smoke.sh 16.59.211.99
```

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

---

## Alcance y limitaciones

Implementado:

- API REST mock.
- Dockerizacion.
- CI/CD y GHCR para API.
- Monitoreo tecnico.
- Ingesta real desde datos.gob.ar.
- Bronze/Silver/Gold/Semantic.
- Dagster para orquestacion.
- Quality checks persistidos.
- Metabase para BI.
- DataHub como catalogo externo de metadata.
- ADRs, runbooks y checklist de entrega.

Limitaciones asumidas:

- No hay modelo predictivo real.
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
