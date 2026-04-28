# ADR-0004: Usar Prometheus, Grafana, Alertmanager y cAdvisor para monitoreo

## Estado

Aceptado

## Contexto

La Fase 1 requiere observar el comportamiento técnico de la API mock y validar requerimientos no funcionales relacionados con disponibilidad, latencia y tasa de errores.

La consigna pide monitorear:

- disponibilidad de la API;
- latencia;
- tasa de errores;
- frecuencia de consultas;
- uso de recursos;
- alertas ante fallas o degradación.

Se consideraron tres caminos:

- stack open-source auto-hosteado: Prometheus + Grafana + Alertmanager;
- SaaS como Datadog o New Relic;
- stack orientado a logs como ELK o Loki.

## Decisión

Se usará:

- **Prometheus** para recolectar métricas y evaluar reglas de alerta;
- **Grafana** para visualizar métricas en un dashboard técnico;
- **Alertmanager** para recibir y rutear alertas;
- **cAdvisor** para exponer métricas de contenedores.

Todo corre en el mismo `docker-compose.yml` junto con la API.

## Consecuencias

Esta decisión permite cubrir las métricas principales de operación:

- Rate: cantidad de requests;
- Errors: tasa de errores 4xx/5xx;
- Duration: latencia;
- disponibilidad mediante `up`;
- recursos de contenedores mediante cAdvisor.

Beneficios:

- herramientas open-source;
- reproducibles localmente;
- integradas con Docker Compose;
- sin costo de SaaS;
- estándar común en sistemas containerizados.

Trade-offs:

- no cubre logs centralizados;
- no cubre tracing distribuido;
- no cubre APM completo;
- la retención de métricas queda limitada al volumen local de Prometheus;
- Alertmanager necesita un `.env` con webhook real si se quiere enviar alertas a Slack.

En sandbox se puede usar un webhook dummy para validar que Alertmanager levante y que las alertas se vean en la UI. El envío real queda condicionado a configurar credenciales reales fuera del repositorio.

Queda fuera de Fase 1: logs estructurados centralizados, tracing, autenticación/SSO en Grafana, alta disponibilidad de Prometheus y backups del historial de métricas.
