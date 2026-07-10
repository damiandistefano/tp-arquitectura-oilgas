# ADR 0019 — Orquestar el retraining con Dagster

## Estado
Aceptado

## Contexto

Adenda 3 pide que el entrenamiento se pueda repetir para un día puntual y que haya retraining recurrente/automático, no solo scripts que corren a mano. Ya usamos Dagster para orquestar el pipeline de datos (ver ADR 0006), así que la pregunta era si sumamos el entrenamiento ahí mismo o si usamos otra herramienta aparte.

## Problema

Necesitamos algo que:
- pueda correr build_features -> train -> gate en orden
- tenga un schedule mensual automático
- se pueda disparar manual para un `as_of_date` puntual, para reproducir un entrenamiento viejo

## Alternativas consideradas

**Airflow**
- Es el estándar de la industria para este tipo de cosas
- Ya se había descartado en el ADR 0006 para el pipeline de datos por ser pesado para una EC2 chica
- Sumar Airflow solo para el entrenamiento significaría tener dos orquestadores en el mismo proyecto, lo cual complica más de lo que resuelve

**Scripts bash con cron**
- Es lo más simple, ya existe `scripts/retrain-model.sh` que encadena los tres pasos
- No tiene UI para ver el historial de corridas
- No separa bien "correr ahora" de "correr programado"

**Dagster (elegida)**
- Ya está levantado para el pipeline de datos, agregar un job nuevo no suma infraestructura
- Los "assets" que ya existen (`build_features`, `train_model`, `promote_model`) se pueden encadenar en un job propio
- Permite tanto correr manual desde la UI con un `as_of_date` como tener un schedule automático

## Decisión

Se agrega `ml_training_job` en `dagster/dwh_pipeline/definitions.py`, que encadena `build_features -> train_model -> promote_model`, más un schedule (`ml_retraining_monthly`) que lo corre una vez por mes. `scripts/retrain-model.sh` sigue existiendo para correr los mismos pasos a mano sin pasar por Dagster, útil para debug rápido.

## Consecuencias

- No hay que aprender ni operar una segunda herramienta de orquestación
- El historial de corridas de entrenamiento se ve en la misma UI que el pipeline de datos (puerto 3002)
- Dagster en modo `dev` no persiste el historial entre reinicios del contenedor, igual que se aclaró en el ADR 0006

## Qué queda fuera

No se usa Airflow ni ningún otro orquestador separado para ML. No hay reintentos sofisticados ni alertas si el retraining falla, más allá de lo que Dagster muestra en su UI.
