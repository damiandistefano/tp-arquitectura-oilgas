# Runbook: Stack Local (Docker Compose)

Este documento describe cómo operar el entorno de desarrollo y pruebas local, incluyendo la API, Prometheus, Grafana, cAdvisor y Alertmanager.

## 1. Cómo levantar el stack
Asegurate de tener Docker y Docker Compose instalados. Ejecutá el siguiente comando en la raíz del proyecto:
```bash
docker compose up -d --build
```
Esto levantará los servicios en background.

## 2. Cómo verificar la API
* **URL Base:** `http://localhost:8000`
* **Health Check:** `http://localhost:8000/health`
* **Documentación Swagger:** `http://localhost:8000/docs`
* **Probar el endpoint (requiere API Key):**
  ```bash
  curl -H "X-API-Key: abcdef12345" "http://localhost:8000/api/v1/forecast?id_well=POZO-001&date_start=2026-03-15&date_end=2026-03-20"
  ```

## 3. Cómo verificar Prometheus y Alertas
* **Prometheus UI:** `http://localhost:9090`
* Ir a **Status -> Targets** para verificar que `oilgas-api` y `cadvisor` estén en estado `UP`.
* **Alertmanager UI:** `http://localhost:9093` para ver alertas disparadas.

## 4. Cómo entrar a Grafana
* **URL:** `http://localhost:3000`
* **Usuario:** `admin`
* **Contraseña:** `admin` 
* Navegar a **Dashboards -> General -> Oil & Gas API Dashboard**.

## 5. Estrategia y Pruebas de Alertas
Las alertas están configuradas en Alertmanager. Para que envíen mensajes a Slack, configurá `SLACK_WEBHOOK_URL` en el archivo `.env` de la raíz del proyecto (que NO se sube a Git).

Hay 4 alertas configuradas en `prometheus/rules/alerts.yml`: `APIDown` (critical), `HighErrorRate` (warning), `HighLatency` (warning) y `APIRecovered` (info). Para validar las tres primeras, se pueden disparar manualmente:

En todos los casos, después de seguir los pasos podés ver la alerta:
* En Prometheus: `http://localhost:9090/alerts` (estado `firing` en rojo).
* En Alertmanager: `http://localhost:9093` (aparece en la lista con su severidad).
* En Slack si el `.env` está configurado con credenciales reales.

### 5.1 APIDown (API caída más de 1 minuto)
1. Bajá el contenedor de la API: `docker compose stop api`
2. Esperá ~70 segundos.
3. Ver la alerta `APIDown` en Prometheus y Alertmanager.
4. Volver a levantarla: `docker compose start api`. La alerta se resuelve.

### 5.2 HighErrorRate (más del 5% de 5xx durante 2 minutos)
La API tiene un endpoint de debug (`/api/v1/debug/fail`) que siempre devuelve 500.
```bash
# Generar 5xx en bucle durante >2 minutos
for i in {1..120}; do
  curl -s -H "X-API-Key: abcdef12345" http://localhost:8000/api/v1/debug/fail > /dev/null
  sleep 1
done
```
Después de ~2 minutos la alerta aparece en estado `firing`. Para que se resuelva, dejá de generar errores y esperá otros ~2 minutos.

### 5.3 HighLatency (P95 mayor a 1s durante 2 minutos)
El mock responde en milisegundos, así que disparar esta alerta requiere inyectar latencia artificialmente (no está implementado en el código). Queda como alerta configurada y validable por inspección:
* Regla cargada: `http://localhost:9090/rules` → grupo `oilgas-api` → `HighLatency`.
* Query subyacente en `http://localhost:9090/graph`:
  ```
  histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{job="oilgas-api"}[5m])) by (le))
  ```

## 6. Cómo ver logs y diagnosticar config
Para ver los logs de todos los servicios en tiempo real:
```bash
docker compose logs -f
```
Logs de un servicio específico:
```bash
docker compose logs -f api
docker compose logs -f prometheus
docker compose logs -f grafana
docker compose logs -f alertmanager
docker compose logs -f cadvisor
```
Si Alertmanager o Prometheus no arrancan, lo más común es que el archivo de config tenga un error. Para validar los rules de Prometheus sin levantar el stack:
```bash
docker exec tp-arquitectura-oilgas-prometheus-1 promtool check rules /etc/prometheus/rules/alerts.yml
docker exec tp-arquitectura-oilgas-prometheus-1 promtool check config /etc/prometheus/prometheus.yml
```

## 7. Troubleshooting

### 7.1 Problemas generales al levantar el stack
* **Puerto ocupado (8000, 3000, 9090, 9093, 8080):** Identificá el proceso con `lsof -i :<puerto>` y bajalo, o cambiá el mapeo en `docker-compose.yml` (ej. `"8001:8000"`).
* **Error de permisos Docker (Linux):** Agregá tu usuario al grupo `docker` o ejecutá con `sudo`.
* **`.env` no existe:** Alertmanager falla al arrancar porque no puede sustituir las variables. Copiá `.env.example` a `.env` antes de levantar el stack.

### 7.2 Prometheus
* **Target `oilgas-api` aparece DOWN en `/targets`:** La API no está respondiendo en `api:8000/metrics`. Revisá `docker compose logs api`. Si la API está up, verificá que el puerto no esté mapeado distinto en el compose.
* **Target `cadvisor` DOWN:** cAdvisor puede tardar 10-15s en responder tras arrancar. Si sigue DOWN después de 30s, revisá `docker compose logs cadvisor` — en Mac a veces los volúmenes de `/sys` o `/var/lib/docker` fallan.
* **Alerta no aparece en `/alerts`:** Validá los rules con `promtool check rules` (ver sección 6). Si hay error de sintaxis la regla no se carga.
* **Falta una métrica:** Chequeá directamente el endpoint `/metrics` de la API (`curl http://localhost:8000/metrics`). Si no está ahí, es problema del instrumentator, no de Prometheus.

### 7.3 Grafana
* **Paneles muestran "No data":** Primera check — rango de tiempo arriba a la derecha (poner "Last 5 minutes"). Segunda check — generar tráfico con `curl` para que haya métricas nuevas. Tercera check — verificar que el datasource está OK en **Connections -> Data sources -> Prometheus -> Save & test**.
* **"Datasource prometheus was not found":** El dashboard referencia `"uid": "prometheus"` pero el datasource no tiene ese uid explícito. Verificar que `grafana/provisioning/datasources/prometheus.yml` tiene la línea `uid: prometheus`.
* **Dashboard no aparece:** Revisar que el archivo `grafana/dashboards/oilgas.json` exista y sea JSON válido. Forzar rebuild: `docker compose up -d --build grafana`.
* **Cambios en el dashboard se pierden al reiniciar:** El provisioner está en modo read-only (`allowUiUpdates: false`) — es intencional. Los cambios tienen que hacerse editando el JSON en el repo.

### 7.4 Alertmanager
* **Alerta disparada en Prometheus pero no llega a Alertmanager:** Verificá en Prometheus `http://localhost:9090/status` que la sección "Alertmanagers" apunte a `alertmanager:9093` y esté activa. Si no, revisá la sección `alerting` de `prometheus.yml`.
* **Alertmanager no arranca (exit code != 0):** Revisar `docker compose logs alertmanager`. Errores comunes:
  * `unsupported scheme ""` → las variables `${SLACK_WEBHOOK_URL}` no se sustituyeron porque el `.env` está vacío o mal armado.
  * YAML inválido → probablemente la edición del template rompió el formato.
* **No llegan mensajes a Slack:** Verificar que el `.env` tenga el `SLACK_WEBHOOK_URL` real (no el placeholder del `.env.example`). El webhook se prueba con `curl -X POST -H 'Content-Type: application/json' --data '{"text":"test"}' $SLACK_WEBHOOK_URL`.

## 8. Cómo reiniciar servicios
Si hiciste cambios en el código o configuración, reconstruí y reiniciá:
```bash
docker compose up -d --build
```
Si un servicio se colgó (sin cambios en código):
```bash
docker compose restart api
```