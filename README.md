# tp-arquitectura-oilgas

API REST mock para consulta de pronósticos de producción de pozos de petróleo/gas, con contenedores Docker, CI/CD, monitoreo técnico y despliegue en sandbox.

El objetivo de esta Fase 1 es validar una base técnica de desarrollo ágil: API mock, contrato OpenAPI, Docker, pipeline de CI, artefacto Docker publicable, observabilidad y operación básica del sandbox.

---

## Componentes

| Componente | Qué hace |
|---|---|
| **API (FastAPI)** | Expone endpoints REST protegidos con API Key y documentación OpenAPI/Swagger. |
| **Prometheus** | Scrapea métricas de la API y evalúa reglas de alerta. |
| **Grafana** | Muestra dashboard técnico con requests, errores, latencia, disponibilidad y métricas de contenedores. |
| **Alertmanager** | Recibe alertas de Prometheus y puede rutearlas a Slack mediante webhook. |
| **cAdvisor** | Expone métricas de recursos de contenedores para Prometheus. |
| **GHCR** | Registry donde se publica la imagen Docker de la API desde CI. |

---

## API mock

La API implementa los endpoints pedidos para la integración externa de pronósticos.

### Autenticación

Todos los endpoints funcionales requieren el header:

```http
X-API-Key: abcdef12345
```

Si la API Key falta o es incorrecta, la API devuelve:

```http
403 Forbidden
```

### Endpoints principales

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/v1/wells?date_query=YYYY-MM-DD` | Devuelve pozos activos para la fecha consultada. |
| `GET` | `/api/v1/forecast?id_well=POZO-001&date_start=YYYY-MM-DD&date_end=YYYY-MM-DD` | Devuelve un pronóstico mock diario para el pozo y rango indicado. |
| `GET` | `/health` | Health check del servicio. |
| `GET` | `/metrics` | Métricas Prometheus. |
| `GET` | `/docs` | Documentación Swagger/OpenAPI. |

Ejemplos:

```bash
curl -H "X-API-Key: abcdef12345" \
  "http://localhost:8000/api/v1/wells?date_query=2026-03-15"

curl -H "X-API-Key: abcdef12345" \
  "http://localhost:8000/api/v1/forecast?id_well=POZO-001&date_start=2026-03-15&date_end=2026-03-20"
```

La respuesta de `/api/v1/forecast` usa datos mock determinísticos. Esto permite repetir pruebas y comparar resultados sin depender de un modelo predictivo real, que queda fuera del alcance de la Fase 1.

---

## Cómo levantar el stack local

Requisitos:

- Docker Desktop o Docker Engine.
- Docker Compose.

Desde la raíz del repo:

```bash
cp .env.example .env
docker compose up --build
```

Servicios locales:

| URL | Qué es | Credenciales |
|---|---|---|
| http://localhost:8000/docs | Swagger de la API | Header `X-API-Key: abcdef12345` |
| http://localhost:8000/metrics | Métricas Prometheus | — |
| http://localhost:9090 | Prometheus | — |
| http://localhost:3000 | Grafana | `admin` / `admin` |
| http://localhost:9093 | Alertmanager | — |
| http://localhost:8080 | cAdvisor | — |

Para generar tráfico y poblar el dashboard:

```bash
bash scripts/generate_traffic.sh
```

Para bajar el stack:

```bash
docker compose down
```

---

## Alertas

Las reglas de alerta están definidas en `prometheus/rules/alerts.yml`.

Alertas principales:

- `APIDown`: la API no responde.
- `HighErrorRate`: tasa alta de errores 5xx.
- `HighLatency`: latencia P95 por encima del umbral definido.
- `APIRecovered`: la API vuelve a estar disponible luego de una caída.

Alertmanager puede enviar alertas a Slack si se configura un webhook real en `.env`:

```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

En sandbox se puede usar un valor dummy para validar que Alertmanager levante sin exponer credenciales reales. En ese caso, las alertas se ven en Prometheus/Alertmanager pero no llegan a Slack.

---

## Tests y validaciones locales

Instalar dependencias de desarrollo:

```bash
pip install -r requirements-dev.txt
```

Correr análisis estático y tests:

```bash
ruff check .
pytest -q
```

Validar scripts y Docker Compose:

```bash
bash -n scripts/deploy.sh
bash -n scripts/rollback.sh
bash -n scripts/sandbox-smoke.sh
bash -n scripts/generate_traffic.sh
bash -n scripts/initial_setup.sh

docker compose config
docker compose build api
```

---

## CI/CD

El pipeline de GitHub Actions ejecuta:

- instalación de dependencias;
- análisis estático con Ruff;
- tests automatizados con Pytest;
- validación de OpenAPI;
- validación de endpoints protegidos por API Key;
- build de imagen Docker;
- escaneo de vulnerabilidades con Trivy;
- smoke test del contenedor;
- validación de scripts;
- validación de `docker-compose.yml` y `docker-compose.deploy.yml`;
- chequeo de archivos sensibles trackeados;
- smoke test del stack completo;
- validación de métricas, targets y reglas de Prometheus.

En `main`, el pipeline publica la imagen de la API en GitHub Container Registry (GHCR) con tags:

- `latest`;
- commit SHA.

---

## Deploy a EC2 sandbox

La estrategia de deploy está documentada en:

- [docs/deployment-strategy.md](docs/deployment-strategy.md)
- [docs/runbooks/deploy-aws.md](docs/runbooks/deploy-aws.md)
- [docs/runbooks/sandbox-validation.md](docs/runbooks/sandbox-validation.md)

El flujo recomendado de release usa la imagen publicada en GHCR y `docker-compose.deploy.yml`:

```bash
IMAGE_TAG=<commit_sha> ./scripts/deploy.sh
```

Para rollback:

```bash
./scripts/rollback.sh <commit_sha_anterior>
```

También existe `scripts/initial_setup.sh`, que queda como script de bootstrap inicial de EC2. No es el flujo principal de release.

---

## Smoke test del sandbox

Desde una máquina local:

```bash
bash scripts/sandbox-smoke.sh <EC2_PUBLIC_IP>
```

También acepta URL completa:

```bash
bash scripts/sandbox-smoke.sh http://<EC2_PUBLIC_IP>
```

El script valida API, endpoints protegidos, métricas, Prometheus, reglas de alerta, Alertmanager y Grafana.

Además existe un workflow manual:

```text
GitHub Actions → AWS Smoke Test → Run workflow
```

Recibe `base_url`, por ejemplo:

```text
http://52.15.50.130
```

---

## Decisiones de arquitectura

Las decisiones principales están documentadas como ADRs en `docs/adr/`:

- Docker Compose para el stack local.
- GitHub Actions para CI.
- GHCR para publicación de imágenes.
- Prometheus, Grafana, Alertmanager y cAdvisor para monitoreo.
- Trivy para escaneo de vulnerabilidades de imágenes Docker.

---

## Alcance y limitaciones de Fase 1

Implementado en esta fase:

- API REST mock.
- Autenticación básica por API Key.
- Swagger/OpenAPI online.
- Dockerización.
- CI con tests, linting, build, scan y smoke tests.
- Imagen Docker publicable en GHCR.
- Sandbox AWS EC2.
- Monitoreo con Prometheus/Grafana/Alertmanager/cAdvisor.
- Runbooks de operación.
- Rollback por tag/SHA.

Fuera de alcance para esta fase:

- modelo predictivo real;
- ingesta real de datos;
- base de datos productiva;
- separación completa dev/staging/prod;
- canary, blue-green o rolling deployment real;
- Kubernetes;
- performance testing formal con Locust;
- envío real de alertas si no se configura webhook real;
- logs centralizados y tracing distribuido.

Estas decisiones se tomaron porque la Fase 1 busca validar arquitectura base, integración, observabilidad y operación mínima de un mock técnico, evitando sobrediseñar infraestructura antes de tener usuarios productivos reales.

---

## Flujo de trabajo del equipo

El repositorio usa GitFlow simplificado:

```text
feature/* -> develop -> main
```

Reglas principales:

- no commitear directo a `main`;
- trabajar en ramas `feature/*`;
- integrar por Pull Request;
- mantener CI en verde;
- actualizar documentación cuando cambia el uso o la operación del sistema;
- no commitear `.env`, `.pem`, tokens, claves privadas ni credenciales.

Ver [CONTRIBUTING.md](CONTRIBUTING.md) para el detalle del flujo.
