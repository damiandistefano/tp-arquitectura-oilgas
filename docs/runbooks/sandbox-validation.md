# Runbook: Validación Sandbox (EC2)

Quién lo ejecuta y cuándo: integrante responsable de operación, una vez que el deploy en EC2 está activo.

Este runbook sirve para validar que el sandbox de Fase 1 sigue operativo y que los componentes principales responden correctamente.

---

## 1. Pre-requisitos

- API desplegada en EC2.
- Para el stack completo de monitoreo: `docker compose up -d` con `docker-compose.yml`.
- Security Group con inbound abierto desde la IP del equipo en:
  - `22` SSH;
  - `8000` API;
  - `9090` Prometheus;
  - `3000` Grafana;
  - `9093` Alertmanager;
  - `8080` cAdvisor, opcional.
- Archivo `.env` presente en el host EC2.
- IP pública de la instancia.

---

## 2. Servicios expuestos

| Servicio | URL | Credenciales |
|---|---|---|
| API — Swagger | `http://<EC2_PUBLIC_IP>:8000/docs` | Header `X-API-Key: abcdef12345` |
| API — Health | `http://<EC2_PUBLIC_IP>:8000/health` | — |
| API — Metrics | `http://<EC2_PUBLIC_IP>:8000/metrics` | — |
| Prometheus | `http://<EC2_PUBLIC_IP>:9090` | — |
| Grafana | `http://<EC2_PUBLIC_IP>:3000` | `admin` / `admin` |
| Alertmanager | `http://<EC2_PUBLIC_IP>:9093` | — |
| cAdvisor | `http://<EC2_PUBLIC_IP>:8080` | — |

---

## 3. Smoke test automático

Desde la raíz del repo:

```bash
bash scripts/sandbox-smoke.sh <EC2_PUBLIC_IP>
```

También acepta URL completa:

```bash
bash scripts/sandbox-smoke.sh http://<EC2_PUBLIC_IP>
```

El script valida:

- `/health`;
- `/openapi.json`;
- `/metrics`;
- `/api/v1/wells` con API Key y `date_query`;
- `/api/v1/forecast` con API Key;
- rechazo sin API Key;
- health de Prometheus;
- targets de Prometheus;
- reglas de alerta;
- health de Alertmanager;
- health de Grafana;
- datasource Prometheus en Grafana.

Sale con código `0` si todo pasa y `1` si algún check falla.

Como alternativa desde CI, el workflow `.github/workflows/aws-smoke.yml` corre checks básicos desde GitHub Actions. Se activa manualmente con `workflow_dispatch` desde la pestaña Actions.

---

## 4. Checklist manual

Completar tras el smoke test para dejar evidencia de entrega.

### API

- [ ] `GET /health` responde 200 y contiene `"status":"healthy"`.
- [ ] `GET /openapi.json` responde 200.
- [ ] `GET /docs` renderiza Swagger UI.
- [ ] `GET /metrics` expone `http_requests_total`.
- [ ] `GET /api/v1/wells?date_query=2026-03-15` con `X-API-Key: abcdef12345` responde 200.
- [ ] `GET /api/v1/forecast?id_well=POZO-001&date_start=2026-03-15&date_end=2026-03-20` con API Key responde 200.
- [ ] `GET /api/v1/wells?date_query=2026-03-15` sin header responde 403.

### Prometheus

- [ ] `http://<EC2_PUBLIC_IP>:9090/targets` muestra `oilgas-api` en estado **UP**.
- [ ] `http://<EC2_PUBLIC_IP>:9090/rules` muestra reglas cargadas: `APIDown`, `HighErrorRate`, `HighLatency`, `APIRecovered`.

### Grafana

- [ ] Login con `admin` / `admin` funciona.
- [ ] Datasource Prometheus está OK.
- [ ] Dashboard `Oil & Gas API Dashboard` muestra paneles con datos.

### Alertmanager

- [ ] UI accesible en `:9093`.
- [ ] No hay alertas inesperadas en `firing` al momento de validar.
- [ ] Si se usa `.env` dummy, queda documentado que no se envían mensajes reales a Slack.

---

## 5. Generar tráfico hacia EC2

Para poblar métricas del dashboard:

```bash
API=http://<EC2_PUBLIC_IP>:8000 bash scripts/generate_traffic.sh
```

También se acepta:

```bash
API_URL=http://<EC2_PUBLIC_IP>:8000 bash scripts/generate_traffic.sh
```

El script genera tráfico válido, errores 403 y errores 500 de debug para validar métricas y alertas.

---

## 6. Validación opcional de alertas

Aplica al stack completo (`docker-compose.yml`). Si solo se levantó la API con `docker-compose.deploy.yml`, primero levantar monitoreo.

### Disparar APIDown

En la EC2:

```bash
docker compose stop api
```

Esperar aproximadamente 1 minuto. Prometheus debería mostrar `APIDown` en firing y Alertmanager debería recibir la alerta.

Para recuperar:

```bash
docker compose start api
```

O redeployar desde GHCR:

```bash
IMAGE_TAG=latest ./scripts/deploy.sh
```

En sandbox con `.env` dummy, las alertas aparecen en la UI de Alertmanager pero no llegan a Slack.

---

## 7. Troubleshooting

### Comandos básicos en EC2

```bash
docker compose ps
docker compose logs -f api
docker compose logs -f prometheus
docker compose logs -f grafana
docker compose logs -f alertmanager
docker compose restart <servicio>
docker compose down && docker compose up -d
```

### Casos frecuentes

| Síntoma | Causa probable | Solución |
|---|---|---|
| Conexión rechazada a cualquier puerto | Security Group cerrado | Agregar inbound rule para la IP del equipo. |
| `/metrics` no aparece en Prometheus targets | Scrape incorrecto o API caída | Verificar `prometheus.yml` y logs de API. |
| Grafana no carga datasource | Prometheus no arrancó o no está accesible | Revisar `docker compose ps` y reiniciar Prometheus/Grafana. |
| Alertmanager no levanta | `.env` ausente o mal formado | Crear `.env` desde `.env.example` o `.env.sandbox.example`. |
| Slack no recibe alertas | Webhook dummy o inválido | Configurar `SLACK_WEBHOOK_URL` real fuera de Git. |
| `docker compose` no existe | Docker Compose plugin no instalado | Instalar Docker Compose plugin en la instancia. |

Para troubleshooting más detallado de Prometheus, Grafana y Alertmanager, ver [local-stack.md](local-stack.md).

---

## 8. Evidencia final

Completar antes de entregar:

| Item | Estado | Notas |
|---|---|---|
| Output de `scripts/sandbox-smoke.sh` con exit 0 | [ ] | Pegar output o adjuntar captura. |
| Screenshot del dashboard de Grafana | [ ] | Mostrar paneles con datos reales. |
| Screenshot de Prometheus targets | [ ] | `oilgas-api` en UP. |
| Screenshot de reglas de alerta | [ ] | Mostrar reglas cargadas. |
| Screenshot de Alertmanager | [ ] | Estado limpio o alerta de prueba. |
| URLs activas el día de entrega | [ ] | Completar tabla de servicios. |

---

## 9. Release tag sugerido

Una vez que `develop` esté mergeado a `main` y CI esté verde:

```bash
git checkout main
git pull origin main
git tag v0.1.0
git push origin v0.1.0
```

Crear release en GitHub con un changelog breve y link a este runbook.
