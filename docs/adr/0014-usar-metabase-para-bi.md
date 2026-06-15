# ADR 0014 - Usar Metabase para BI

## Estado

Aceptado.

## Contexto

La Adenda 2 pide una plataforma de BI para que usuarios no tecnicos puedan revisar los datos. El pipeline ya deja vistas en `semantic.*` y resultados de calidad en `quality.data_quality_results`, asi que la herramienta de BI tenia que conectarse a PostgreSQL y permitir armar un dashboard entendible sin escribir codigo nuevo.

## Problema

Si el consumo queda solo en SQL o en tablas del warehouse, la demo se vuelve demasiado tecnica. Tambien aparece el riesgo de que cada consulta calcule metricas distintas. Necesitamos una capa visual para negocio, pero sin esconder la logica principal dentro del dashboard.

## Alternativas consideradas

### Grafana

Grafana ya existe en el proyecto para monitoreo tecnico de la API. Podria conectarse a PostgreSQL, pero esta mejor orientado a metricas operativas, targets, alertas y series tecnicas. Para preguntas de negocio sobre produccion, operadoras y areas, Metabase resulta mas directo.

### Apache Superset

Superset es potente para BI y exploracion, pero suma mas configuracion y administracion. Para esta entrega era mas pesado que lo necesario.

### Metabase

Metabase permite conectarse rapido a PostgreSQL, crear preguntas SQL, armar dashboards y compartir una vista simple para usuarios de negocio. La contra es que el dashboard queda configurado desde la UI y no completamente provisionado como codigo.

## Decision

Usamos Metabase como plataforma de BI local/sandbox. El dashboard principal es `Oil & Gas BI Dashboard` y consume vistas `semantic.*` mas `quality.data_quality_results`.

La logica de negocio principal queda versionada en dbt, no en Metabase. Metabase se usa para visualizar y explorar, no para definir las transformaciones centrales.

## Consecuencias

- Usuarios no tecnicos pueden revisar produccion mensual, produccion por operadora, produccion por area/yacimiento, frescura y estado de calidad.
- El dashboard se puede reconstruir con el runbook de BI si se pierde el volumen local de Metabase.
- Las metricas importantes se mantienen en vistas SQL versionadas, reduciendo SQL duplicado dentro de la herramienta.
- No hay provisioning automatico del dashboard por API de Metabase. Para esta entrega se acepta porque automatizarlo requiere manejar tokens, IDs internos y estado del volumen.

## Fuera de alcance

No se implementa una plataforma BI productiva con SSO, permisos finos, versionado automatico de dashboards ni promocion entre ambientes. El alcance es un dashboard academico reproducible por runbook y validado visualmente.
