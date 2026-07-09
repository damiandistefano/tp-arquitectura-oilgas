# ADR 0016 — Usar MLflow para tracking y registry

## Estado
Aceptado

## Contexto

Adenda 3 pide que el entrenamiento sea reproducible: se tiene que poder ver qué parámetros y métricas tuvo cada corrida, y cuál es el modelo activo en un momento dado. Sin nada de esto, cada entrenamiento pisa al anterior y no queda registro de nada.

## Problema

Necesitamos algo que:
- guarde parámetros, métricas y el modelo de cada corrida de entrenamiento
- tenga un concepto de "modelo activo" (el champion) que la API pueda consultar
- no sea pesado de levantar para un proyecto de facultad

## Alternativas consideradas

**Weights & Biases**
- Muy usado en la industria, buena UI
- Es un servicio externo (cloud), no encaja con que todo el stack corra local con docker compose
- Complica la entrega si alguien no tiene cuenta

**Solo artifacts locales (carpeta con json + pickle)**
- Es lo más simple, no agrega ningún servicio nuevo
- No tiene UI para comparar corridas
- No tiene un concepto real de "registry" con alias, hay que inventarlo a mano

**MLflow (elegida)**
- Se levanta como un contenedor más en el docker compose, con backend sqlite
- Tiene tracking (runs, métricas, parámetros) y registry (versiones de modelo, alias) en la misma herramienta
- Es la que se vio en las clases prácticas de la materia

## Decisión

Usamos MLflow como servicio (`mlflow` en docker-compose.yml, puerto 5000). El training (`ml/train.py`) loguea el run y el modelo ahí si `MLFLOW_TRACKING_URI` está seteado, y el gate de promoción (`ml/promotion_gate.py`) mueve el alias `champion` a la versión que gana.

Como fallback, si MLflow no está disponible, el training igual guarda todo en `ml_artifacts/` (carpeta local con el modelo y un `champion.json`), y la API puede usar eso. Esto es explícito y se ve en la respuesta de la API como `source: local_fallback`, no se disfraza de MLflow.

## Consecuencias

- Hay un contenedor más para levantar (`mlflow`), con su propio Dockerfile
- El modelo activo se identifica por nombre + alias (`oilgas_forecaster` / `champion`), no por un path hardcodeado
- Si MLflow se cae, el sistema sigue funcionando con el fallback local, pero se pierde la comparación de corridas hasta que vuelva

## Qué queda fuera

No usamos un backend de base de datos real para MLflow (queda en sqlite dentro del contenedor), ni un artifact store externo tipo S3. Para esta entrega alcanza con que persista en el volumen de Docker.
