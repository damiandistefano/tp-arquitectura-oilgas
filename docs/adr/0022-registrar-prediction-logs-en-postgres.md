# ADR 0022 — Registrar prediction logs en Postgres

## Estado
Aceptado

## Contexto

Adenda 3 pide observabilidad mínima del modelo en producción: poder ver qué se predijo, cuándo, con qué modelo y si falló. Sin esto, si algo sale mal en una predicción no hay forma de investigar después qué pasó.

## Problema

Necesitamos guardar, por cada request a `/api/v1/forecast`:
- qué pozo y rango de fechas se pidió
- qué modelo respondió (nombre, versión, run_id, si vino de MLflow o del fallback local)
- si la respuesta fue exitosa o hubo error, y cuánto tardó

## Alternativas consideradas

**Loguear a archivo o a stdout**
- Es lo más simple de implementar
- Para consultar "cuántas veces se usó el fallback local esta semana" hay que parsear logs de texto a mano
- No se integra bien con el resto del stack, que ya usa Postgres para todo lo demás

**Mandar esto a Prometheus/Grafana**
- Ya tenemos Prometheus para métricas de la API
- Prometheus es para series numéricas (contadores, latencias), no para guardar el detalle de cada predicción individual con su payload
- Sirven para cosas distintas, no son reemplazo uno del otro

**Tabla en Postgres (elegida)**
- Ya tenemos Postgres levantado y la API ya se conecta ahí
- Permite consultas SQL directas para la demo ("mostrame las últimas predicciones y qué modelo las sirvió")
- Se puede cruzar fácil con `feature_reference_stats` para drift, o con el registro de champions

## Decisión

Se agrega la tabla `metadata.prediction_logs`, con una fila por request a `/api/v1/forecast`: pozo, rango pedido, metadata del modelo (nombre, versión, alias, run_id, source), si fue éxito o error, latencia y un resumen de la respuesta. La escribe `app/prediction_logging.py` en cada request, tanto si la predicción salió bien como si falló.

## Consecuencias

- Cada predicción queda auditada, se puede ver después qué modelo la sirvió
- Agrega una escritura a Postgres por cada request, que es aceptable para el volumen de este proyecto
- Si Postgres estuviera caído, ya la API no puede leer features tampoco, así que no es una dependencia nueva

## Qué queda fuera

No hay un dashboard armado sobre esta tabla en esta entrega (se consulta con SQL directo). No se loguean las features usadas en detalle, solo el resumen y la metadata del modelo.
