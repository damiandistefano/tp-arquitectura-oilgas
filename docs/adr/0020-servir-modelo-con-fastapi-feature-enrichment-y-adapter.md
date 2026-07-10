# ADR 0020 - Servir modelo con FastAPI, feature enrichment y adapter

## Estado

Aceptado

Fecha: 2026-07-08

## Contexto y planteamiento del problema

Adenda 3 pide que `/api/v1/forecast` deje de ser un mock diario con
`id_well` y pase a servir forecast mensual de `prod_pet` con contrato
`id_pozo`. La API ya existe en FastAPI y el repo incorporo feature store,
training y artifacts locales, pero esas piezas no deben quedar acopladas en
cada handler HTTP.

La decision es como conectar la API con features, modelo activo y logs de
prediccion sin prometer una plataforma productiva ni pisar el ownership de
training/drift.

## Criterios de decision

- Reversibilidad: debe poder cambiarse el backend de modelo sin reescribir el
  contrato HTTP.
- Simplicidad: alcanza un serving REST stateless para el sandbox academico.
- Mantenibilidad: la API no deberia conocer detalles de MLflow ni SQL fisico en
  todos lados.
- Integracion: debe usar `features.pozo_monthly_features`, modelo
  `oilgas_forecaster` alias `champion` y logs en `metadata.prediction_logs`.
- Riesgo: si MLflow o Postgres no estan listos, el error debe ser claro y el
  fallback local debe ser visible.

## Opciones consideradas

### Opcion A - FastAPI + adapters propios

Mantener FastAPI y sumar modulos internos:

- `feature_lookup.py` para leer features.
- `model_registry.py` para MLflow/artifacts locales.
- `ml_inference.py` para normalizar predicciones.
- `prediction_logging.py` para persistir metadata.

Pros:

- Reusa la API, auth, health y metrics existentes.
- Se testea con monkeypatch/fixtures sin DB o MLflow reales.
- El contrato publico queda separado de MLflow y del SQL.
- Permite fallback local visible para demo.

Contras:

- No resuelve escalado avanzado, canary ni autoscaling de modelos.
- La API sigue siendo responsable de orquestar lookup, modelo y logging.

### Opcion B - API acoplada directo a MLflow y SQL

El handler `/api/v1/forecast` podria consultar Postgres, llamar MLflow y
guardar logs directamente.

Pros:

- Menos archivos al principio.
- Camino rapido para una prueba manual.

Contras:

- Dificulta tests unitarios.
- Mezcla contrato HTTP, queries, registry y transformacion de salida.
- Cambiar MLflow por artifacts locales o ajustar el feature store obliga a
  tocar el endpoint.

### Opcion C - Ray Serve, SageMaker o TensorFlow Serving

Montar un servidor especializado de modelos y dejar FastAPI como proxy o
cliente.

Pros:

- Mejor encaje para serving productivo con escalado y despliegues de modelos.
- Abre opciones de autoscaling, versiones y ruteo avanzado.

Contras:

- Fuera del alcance de este proyecto y de la infraestructura actual.
- Agrega dependencias y operacion que no aportan al objetivo de la Fase 3.
- Puede confundir el alcance prometiendo madurez productiva que no existe.

### Opcion D - Cliente envia todas las features

La API podria recibir el vector completo de features en el request.

Pros:

- Evita consultar Postgres durante la inferencia.
- Simplifica el endpoint desde el lado servidor.

Contras:

- Rompe el contrato cerrado de `id_pozo + periodo_mes`.
- Expone detalles internos de feature engineering al cliente.
- Es mas facil introducir leakage o columnas inconsistentes.

## Resultado de la decision

Elegimos la Opcion A: FastAPI con feature enrichment interno y adapter de
modelo. Es el camino mas simple y reversible para el sandbox: mantiene la API
existente, separa responsabilidades y permite intentar MLflow cuando
`MLFLOW_TRACKING_URI` esta configurado y la dependencia esta disponible. Si no,
usa artifact local o fallback local visible.

El cliente solo envia `id_pozo`, `date_start` y `date_end`. La API busca
features en Postgres, carga el modelo activo por `model_registry.py`, devuelve
metadata runtime y persiste un log de inferencia.

## Como se valida

Validaciones automatizadas:

```bash
python -m pytest tests/test_api.py tests/test_feature_lookup.py tests/test_model_registry.py tests/test_model_serving.py tests/test_prediction_logging.py -q
python -m ruff check .
bash -n scripts/*.sh
docker compose config
```

Smoke manual:

```bash
bash scripts/api-forecast-smoke.sh
```

Para la demo final, con features y modelo/fallback disponibles,
`/api/v1/forecast` debe responder `200` con `id_pozo`, `target = prod_pet`,
predicciones mensuales y metadata de modelo. El `404` o `503` controlado del
smoke solo es aceptable durante integracion parcial, cuando todavia faltan
features en Postgres o modelo activo.

## Consecuencias y trade-offs

- La API queda lista para integrarse con MLflow real y con artifacts locales.
- `model.version` y `run_id` salen del registry/artifact runtime, no de una
  respuesta mock.
- El fallback local se ve como `local_fallback`; no simula ser MLflow.
- Se agrega una tabla de auditoria minima en Postgres.
- Para servir artifacts sklearn locales, la imagen de API instala dependencias
  minimas de serving (`pandas`, `scikit-learn`, `joblib`) y monta
  `ml_artifacts` como solo lectura.
- No se implementa Ray Serve, SageMaker, TensorFlow Serving, HITL ni drift
  monitoring completo en este bloque.
- Si el feature store no tiene filas para el pozo/rango, la API no inventa
  datos: devuelve error controlado.

## Mas informacion

- [Contratos tecnicos - Adenda 3](../contracts.md)
- [Serving de inferencia forecast](../inference-serving.md)
