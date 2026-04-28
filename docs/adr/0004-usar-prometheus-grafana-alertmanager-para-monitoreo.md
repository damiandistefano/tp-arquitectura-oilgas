# ADR-0004: Usar Prometheus, Grafana y Alertmanager para el monitoreo

## Estado
Aceptado

## Contexto
La Fase 1 requiere que podamos observar la salud de la API (disponibilidad, latencia, tasa de errores) y recibir notificaciones cuando algo falla. El TP se corre localmente sin presupuesto para servicios SaaS y se espera que cualquier integrante pueda levantar el stack completo desde el repo sin depender de cuentas externas.

Se consideraron tres caminos:
* Stack open-source auto-hosteado (Prometheus + Grafana + Alertmanager).
* SaaS como Datadog o New Relic, que aportan mucho pero requieren cuenta, credenciales y tienen costo.
* ELK o stack similar orientado a logs, que cubre otro caso de uso distinto al de métricas.

## Decisión
Se usa **Prometheus** para el scrape de métricas y la evaluación de reglas de alerta, **Grafana** para la visualización (dashboard único provisionado desde un JSON en el repo) y **Alertmanager** para el routing de alertas a Slack. Se suma **cAdvisor** como exporter de métricas de containers. Todo corre en el mismo `docker-compose.yml` junto con la API.

## Consecuencias
Prometheus + Grafana + Alertmanager son el stack estándar de facto para monitoreo de métricas en sistemas containerizados. Son open-source, gratuitos, reproducibles sin credenciales externas y tienen documentación extensa. La separación entre scraper, visualizador y router de alertas es la convención esperada por cualquiera que conozca el ecosistema.

Como trade-offs:
* No cubre **logs** centralizados (eso requeriría Loki o ELK). Los logs se consultan con `docker compose logs`.
* No cubre **tracing distribuido** (Jaeger, Tempo). No es crítico para una API con 3 endpoints.
* No cubre **APM** (Datadog, New Relic). Fuera del scope de un TP.
* La retención de métricas queda limitada al volumen local de Prometheus — sin long-term storage tipo Thanos ni backups.
* Alertmanager requiere un `.env` con credenciales reales (Slack webhook, SMTP) para enviar notificaciones; sin eso, las alertas sólo quedan visibles en la UI.

Queda fuera de Fase 1: logs estructurados centralizados, tracing, autenticación/SSO en Grafana, alta disponibilidad del propio Prometheus y backups del historial de métricas.
