# ADR-0004: Usar Prometheus, Grafana, Alertmanager y cAdvisor para monitoreo

## Estado

Aceptado

## Contexto

La Fase 1 requiere observar el comportamiento técnico de la API mock: disponibilidad, latencia,
tasa de errores y uso de recursos de contenedores. También pide alertas ante caídas o degradación.

El stack tiene que levantar localmente junto con la API (un solo `docker compose up`) y ser
reproducible sin depender de cuentas SaaS ni infraestructura externa.

## Alternativas consideradas

### Prometheus + Grafana + Alertmanager + cAdvisor (opción elegida)

Stack open-source estándar en sistemas containerizados. Prometheus scrapea métricas en formato
`/metrics`, Grafana las visualiza, Alertmanager las enruta a Slack y cAdvisor expone métricas de
los propios contenedores.

Por qué nos convenía:
- `prometheus-fastapi-instrumentator` instrumenta la API con un `@app.on_event("startup")` y
  expone `/metrics` sin tocar la lógica de negocio;
- todos los componentes corren en contenedores, encajan directo en `docker-compose.yml`;
- no hay límites de retención, costo ni dependencia de cuenta SaaS;
- el equipo conocía Prometheus/Grafana del práctico.

Limitaciones que aceptamos:
- la retención de métricas queda en el volumen local de Prometheus; al bajar el stack, el historial
  se pierde si no se persiste el volumen;
- no cubre logs centralizados ni tracing distribuido;
- Alertmanager necesita un webhook Slack real para que las alertas lleguen (con dummy solo se ven
  en la UI).

### Datadog / New Relic (SaaS)

Plataformas con APM completo, logs, trazas y dashboards listos en minutos.

Por qué no las elegimos: requieren una cuenta, configurar agentes y exponer datos del sistema a
una plataforma externa. Para un sandbox académico eso agrega fricción sin aportar aprendizaje
relevante. El costo en el tier gratuito también tiene límites que podían ser un problema en
un entorno compartido.

### ELK (Elasticsearch + Logstash + Kibana) o Grafana Loki

Stacks orientados a logs. Kibana puede hacer algunas métricas, pero su punto fuerte son logs
estructurados y full-text search.

Por qué no los elegimos: el requerimiento de Fase 1 pide métricas de request rate / latencia / error rate, que
se ajustan mejor al modelo pull de Prometheus que al modelo push de logs. ELK además es pesado
en memoria para un sandbox EC2 pequeño. Loki es más liviano, pero agrega complejidad sin que el
requerimiento lo pidiera.

## Decisión

Se usa Prometheus + Grafana + Alertmanager + cAdvisor. Todo corre en `docker-compose.yml` junto
con la API. El dashboard provisiona automáticamente desde `grafana/dashboards/oilgas.json`.

Las alertas configuradas son: `APIDown`, `HighErrorRate`, `HighLatency` y `APIRecovered`.

## Consecuencias

El equipo puede ver estado de la API, latencia P95, tasa de errores y recursos de contenedores
desde `localhost:3000` sin configuración manual.

Trade-offs que quedan:
- si el stack baja y no se persiste el volumen de Prometheus, el historial de métricas se pierde;
- no hay logs centralizados: para debuggear hay que usar `docker compose logs`;
- Alertmanager enruta solo a Slack en esta fase; agregar email requeriría configurar SMTP;
- autenticación de Grafana es básica (`admin` con password compartido de sandbox); no es adecuado para acceso público real.

Queda fuera: logs estructurados, tracing distribuido, APM completo, SSO en Grafana, alta
disponibilidad de Prometheus y retención de métricas a largo plazo.
