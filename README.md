# tp-arquitectura-oilgas

API REST mock de predicción de producción de pozos de petróleo/gas, con stack completo de monitoreo.

---

## Lo que hay en este repo

| Servicio | Qué hace |
|---|---|
| **API (FastAPI)** | Endpoints REST con autenticación por API Key. Expone métricas en `/metrics` |
| **Prometheus** | Scrapea las métricas de la API cada 15s. Tiene 4 reglas de alerta configuradas |
| **Grafana** | Dashboard con 7 paneles: requests, errores, latencia, estado de la API |
| **Alertmanager** | Manda alertas a Slack cuando algo se rompe |

---

## Cómo levantarlo

Necesitás tener Docker Desktop corriendo.

```bash
cp .env.example .env
docker compose up --build
```

Y listo. Los servicios quedan en:

| URL | Qué es | Credenciales |
|---|---|---|
| http://localhost:8000/docs | Swagger de la API | Header: `X-API-Key: abcdef12345` |
| http://localhost:8000/metrics | Métricas Prometheus | — |
| http://localhost:9090 | Prometheus | — |
| http://localhost:3000 | Grafana | admin / admin |
| http://localhost:9093 | Alertmanager | — |

Para ver datos en el dashboard de Grafana, tirarle algunos requests a la API:

```bash
curl -H "X-API-Key: abcdef12345" "http://localhost:8000/api/v1/wells?date_query=2024-01-01"
curl -H "X-API-Key: abcdef12345" "http://localhost:8000/api/v1/forecast?id_well=POZO-001&date_start=2024-01-01&date_end=2024-01-31"
```

---

## Configurar alertas (Slack)

Editá el `.env` con un webhook real de Slack:

```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

Las alertas configuradas:
- `APIDown` (critical): la API no responde por más de 1 minuto.
- `HighErrorRate` (warning): más del 5% de los requests devuelven 5xx.
- `HighLatency` (warning): la latencia P95 supera 1 segundo.
- `APIRecovered` (info): la API volvió a estar disponible tras un downtime y se mantuvo estable 5 minutos.

---

## Correr los tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

Hay 5 tests: 3 de autenticación/endpoints y 2 específicos del endpoint `/metrics`.

---

## Deploy a EC2 (sandbox)

El stack se puede desplegar en una instancia EC2 desde la imagen publicada en GHCR. Ver:

- [docs/runbooks/deploy-aws.md](docs/runbooks/deploy-aws.md) — flujo completo de deploy con `scripts/deploy.sh` y rollback.
- [docs/runbooks/sandbox-validation.md](docs/runbooks/sandbox-validation.md) — checklist de validación post-deploy y `scripts/sandbox-smoke.sh`.
- [docs/deployment-strategy.md](docs/deployment-strategy.md) — estrategia general (Big Bang sobre EC2, GHCR, rollback por SHA).

---

## Cómo está organizado el repo

Cada integrante trabajó en su área. Las features se hicieron en branches separadas y se mergean a `develop` primero. El CI corre automáticamente en cualquier branch `feature/**` y en `develop`.

El orden correcto para mergear los PRs es:
1. `feature/prometheus-instrumentation` → agrega `/metrics` a la API
2. `feature/docker-compose-monitoring` → Dockerfile de Prometheus + docker-compose base
3. `feature/grafana-dashboards` → dashboard de Grafana
4. `feature/alerting` → Alertmanager con reglas y notificaciones
5. `feature/ci-enhancements` → smoke test del stack completo + push a GHCR

Cada servicio de monitoreo tiene su propio `Dockerfile` que baja la imagen oficial y le copia la config adentro (en vez de montarla como volumen).
