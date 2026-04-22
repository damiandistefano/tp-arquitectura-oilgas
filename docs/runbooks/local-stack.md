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
* **Contraseña:** `admin` (te pedirá cambiarla en el primer login, podés omitirlo).
* Navegar a **Dashboards -> General -> Oil & Gas API Dashboard**.

## 5. Estrategia y Pruebas de Alertas
Las alertas están configuradas en Alertmanager. Para que envíen mensajes a Slack o Email, debés configurar el archivo `.env` en la raíz del proyecto (que NO se sube a Git) con las variables:
`SLACK_WEBHOOK_URL`, `ALERT_EMAIL`, `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`.

Hay 3 alertas configuradas en `prometheus/rules/alerts.yml`: `APIDown` (critical), `HighErrorRate` (warning) y `HighLatency` (warning). Para validar que funcionan, cada una se puede disparar manualmente.

En todos los casos, después de seguir los pasos podés ver la alerta:
* En Prometheus: `http://localhost:9090/alerts` (estado `firing` en rojo).
* En Alertmanager: `http://localhost:9093` (aparece en la lista con su severidad).
* En Slack/Email si el `.env` está configurado con credenciales reales.

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

## 6. Cómo ver logs
Para ver los logs de todos los servicios en tiempo real:
```bash
docker compose logs -f
```
Para ver logs de un servicio específico (ej. la API):
```bash
docker compose logs -f api
```

## 7. Troubleshooting (Qué hacer si algo no levanta)
* **Puerto ocupado:** Si falla al iniciar porque el puerto 8000 o 3000 está en uso, identificá qué proceso lo usa o cambiá el mapeo en el `docker-compose.yml` (ej. `"8080:8000"`).
* **No hay métricas en Grafana:** Verificá en Prometheus (`http://localhost:9090/targets`) si el target de la API está en rojo. Si es así, revisá los logs de la API.
* **Error de permisos Docker:** Ejecutar con `sudo` si estás en Linux (`sudo docker compose up -d`).

## 8. Cómo reiniciar servicios
Si hiciste cambios en el código o configuración, reconstruí y reiniciá:
```bash
docker compose up -d --build
```
Si un servicio se colgó (sin cambios en código):
```bash
docker compose restart api
```