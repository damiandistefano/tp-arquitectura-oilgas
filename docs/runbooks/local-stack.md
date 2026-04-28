# Runbook: Stack Local (Docker Compose)

Este documento describe cómo levantar, validar y diagnosticar el stack local de Fase 1: API, Prometheus, Grafana, cAdvisor y Alertmanager.

---

## 1. Levantar el stack

Requisitos:

- Docker Desktop o Docker Engine.
- Docker Compose.

Desde la raíz del repo:

```bash
cp .env.example .env
docker compose up -d --build
```

Esto levanta los servicios en background.

Para ver estado:

```bash
docker compose ps
```

Para bajar todo:

```bash
docker compose down
```

---

## 2. Verificar la API

URLs principales:

- Base URL: `http://localhost:8000`
- Health: `http://localhost:8000/health`
- Swagger: `http://localhost:8000/docs`
- Métricas: `http://localhost:8000/metrics`

Ejemplos:

```bash
curl http://localhost:8000/health

curl -H "X-API-Key: abcdef12345" \
  "http://localhost:8000/api/v1/wells?date_query=2026-03-15"

curl -H "X-API-Key: abcdef12345" \
  "http://localhost:8000/api/v1/forecast?id_well=POZO-001&date_start=2026-03-15&date_end=2026-03-20"
```

Sin API Key, los endpoints funcionales deben devolver `403`.

---

## 3. Prometheus

URL:

```text
http://localhost:9090
```

Validaciones:

```bash
curl -f http://localhost:9090/-/healthy
curl -f http://localhost:9090/api/v1/targets
curl -f http://localhost:9090/api/v1/rules
```

En la UI:

- ir a **Status → Targets**;
- verificar que `oilgas-api` esté `UP`;
- verificar que `cadvisor` esté `UP` si está disponible en el entorno.

---

## 4. Grafana

URL:

```text
http://localhost:3000
```

Credenciales:

```text
admin / admin
```

Dashboard:

```text
Dashboards → Oil & Gas API Dashboard
```

Si los paneles muestran `No data`, generar tráfico:

```bash
bash scripts/generate_traffic.sh
```

Esperar aproximadamente 20 segundos y refrescar el dashboard.

---

## 5. Alertmanager

URL:

```text
http://localhost:9093
```

Las alertas están configuradas en:

```text
prometheus/rules/alerts.yml
```

Alertas principales:

- `APIDown`;
- `HighErrorRate`;
- `HighLatency`;
- `APIRecovered`.

Para que Alertmanager envíe a Slack, configurar en `.env`:

```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

Si se usa un webhook dummy, las alertas se ven en la UI pero no se envían a Slack.

---

## 6. Validar alertas

### APIDown

```bash
docker compose stop api
```

Esperar aproximadamente 1 minuto y revisar:

- Prometheus: `http://localhost:9090/alerts`
- Alertmanager: `http://localhost:9093`

Recuperar:

```bash
docker compose start api
```

### HighErrorRate

Generar errores 500:

```bash
for i in {1..120}; do
  curl -s -H "X-API-Key: abcdef12345" \
    http://localhost:8000/api/v1/debug/fail > /dev/null
  sleep 1
done
```

Después de la ventana definida en Prometheus, la alerta debería entrar en `firing`.

### HighLatency

La API mock responde rápido, por lo que esta alerta queda validada principalmente por inspección de regla y dashboard. Para dispararla end-to-end haría falta inyectar latencia artificial o usar un endpoint lento, lo cual queda fuera del alcance de Fase 1.

---

## 7. Logs

Todos los servicios:

```bash
docker compose logs -f
```

Por servicio:

```bash
docker compose logs -f api
docker compose logs -f prometheus
docker compose logs -f grafana
docker compose logs -f alertmanager
docker compose logs -f cadvisor
```

---

## 8. Validación de configuración

Scripts:

```bash
bash -n scripts/deploy.sh
bash -n scripts/rollback.sh
bash -n scripts/sandbox-smoke.sh
bash -n scripts/generate_traffic.sh
bash -n scripts/initial_setup.sh
```

Compose:

```bash
docker compose config
IMAGE_TAG=ci API_PORT=8002 docker compose -f docker-compose.deploy.yml config
```

Prometheus, desde contenedor:

```bash
docker exec tp-arquitectura-oilgas-prometheus-1 promtool check config /etc/prometheus/prometheus.yml
docker exec tp-arquitectura-oilgas-prometheus-1 promtool check rules /etc/prometheus/rules/alerts.yml
```

---

## 9. Troubleshooting

### Puerto ocupado

Si algún puerto está ocupado (`8000`, `3000`, `9090`, `9093`, `8080`):

```bash
lsof -i :8000
```

En Windows, usar PowerShell:

```powershell
netstat -ano | findstr :8000
```

### `.env` no existe

Crear:

```bash
cp .env.example .env
```

### Prometheus no scrapea API

Revisar:

```bash
docker compose logs api
docker compose logs prometheus
curl http://localhost:8000/metrics
```

### Grafana muestra `No data`

1. Generar tráfico con `scripts/generate_traffic.sh`.
2. Revisar rango temporal del dashboard.
3. Validar datasource Prometheus.
4. Confirmar que Prometheus tiene target `oilgas-api` en `UP`.

### Alertmanager no levanta

Revisar:

```bash
docker compose logs alertmanager
```

Errores comunes:

- `.env` ausente;
- `SLACK_WEBHOOK_URL` vacío;
- YAML inválido;
- `entrypoint.sh` sin permisos de ejecución.

---

## 10. Reiniciar servicios

Con rebuild:

```bash
docker compose up -d --build
```

Sin rebuild:

```bash
docker compose restart api
```
