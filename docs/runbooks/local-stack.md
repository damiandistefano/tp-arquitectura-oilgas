# Runbook: Stack Local (Docker Compose)

Este documento describe cómo operar el entorno de desarrollo y pruebas local, incluyendo la API, Prometheus, Grafana, cAdvisor y Alertmanager.

## 1. Cómo levantar el stack
Asegurate de tener Docker y Docker Compose instalados. Ejecutá el siguiente comando en la raíz del proyecto:
```bash
docker-compose up -d --build
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

**Para forzar una alerta (Ej. API caída):**
1. Bajá solo el contenedor de la API: `docker-compose stop api`
2. Esperá ~1 minuto.
3. Revisá Alertmanager (`http://localhost:9093`), verás la alerta `APIDown` disparada.
4. Volvé a levantarla: `docker-compose start api` y la alerta se resolverá enviando el mensaje de recuperación a Slack/Email.

## 6. Cómo ver logs
Para ver los logs de todos los servicios en tiempo real:
```bash
docker-compose logs -f
```
Para ver logs de un servicio específico (ej. la API):
```bash
docker-compose logs -f api
```

## 7. Troubleshooting (Qué hacer si algo no levanta)
* **Puerto ocupado:** Si falla al iniciar porque el puerto 8000 o 3000 está en uso, identificá qué proceso lo usa o cambiá el mapeo en el `docker-compose.yml` (ej. `"8080:8000"`).
* **No hay métricas en Grafana:** Verificá en Prometheus (`http://localhost:9090/targets`) si el target de la API está en rojo. Si es así, revisá los logs de la API.
* **Error de permisos Docker:** Ejecutar con `sudo` si estás en Linux (`sudo docker-compose up -d`).

## 8. Cómo reiniciar servicios
Si hiciste cambios en el código o configuración, reconstruí y reiniciá:
```bash
docker-compose up -d --build
```
Si un servicio se colgó (sin cambios en código):
```bash
docker-compose restart api
```