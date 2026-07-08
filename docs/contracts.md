# Contratos técnicos - Adenda 3 (ML Engineering)

Contrato base cerrado antes de implementar. Feature store, training, API y CI
se modelan contra este documento; cualquier cambio se acuerda acá primero.

## Target y grano

- **Target inicial**: `prod_pet` mensual (producción de petróleo).
- **Grano**: `id_pozo` + `periodo_mes` (primer día del mes).
- **API y JSON en español**: `id_pozo`, `periodo_mes`, `prod_pet`.

## Feature store

- Tabla: `features.pozo_monthly_features` (PK: `id_pozo`, `periodo_mes`).
- Fuente: `gold.fact_produccion_pozo` + `gold.dim_pozo`.
- Features mínimas:
  - `prod_pet_lag_1`, `prod_pet_lag_2`, `prod_pet_lag_3` (meses calendario)
  - `prod_pet_roll_mean_3`, `prod_pet_roll_std_3` (ventana M-3..M-1)
  - `mes`, `anio`
  - `antiguedad_meses` (meses desde el primer mes observado del pozo)
  - Categóricas disponibles: `cuenca`, `provincia`, `clasificacion`, `tipo_reservorio`
- Auditoría: cada corrida se registra en `features.feature_generation_runs`.

## No-leakage

Para el mes M, **toda feature usa solo datos hasta M-1**. Los lags y rolling
stats se calculan sobre un calendario mensual continuo por pozo (un mes
faltante no corre la ventana). `prod_pet` del mes M es solo target, nunca
feature. Hay tests que verifican esta regla (`tests/test_ml_features.py`).

## Split temporal

- Test: **últimos 6 meses** calendario; si la historia no alcanza
  (menos de 12 meses), **últimos 3**.
- Train: todos los meses anteriores al inicio de test. Sin solapamiento.
- Nada de split random: evita métricas irreales por mezcla temporal.

## Baseline y métrica

- **Baseline**: `baseline_pred = prod_pet_lag_1` (persistencia).
- **Métrica primaria del gate**: `mae` (menor es mejor). Se reportan además
  `rmse` y `smape`.
- Modelo y baseline se evalúan sobre las **mismas filas** del set de test
  (filas con target y lag_1 no nulos).

## Gate de promoción

- **Bootstrap**: si no hay champion, el primer modelo válido que supera al
  baseline se promueve.
- **Normal**: con champion existente, el candidato debe superar al baseline
  **y** al champion actual (re-evaluado sobre la misma ventana de test).
- La decisión queda registrada en `ml_artifacts/runs/<run_id>/gate_decision.json`.

## Reference stats

`features.feature_reference_stats` se genera **en el mismo run de training**
(`training_run_id` = run del modelo). Si existe un candidato, existe su
referencia: el drift check nunca se queda sin baseline de comparación.

## Registro de modelos y runtime metadata

- Nombre del modelo: `oilgas_forecaster`; alias del activo: `champion`.
- **MLflow es la fuente primaria** (tracking + registry) cuando
  `MLFLOW_TRACKING_URI` está seteado.
- **Fallback local visible** (sandbox): `ml_artifacts/runs/<run_id>/`
  (`model.pkl` + `metrics.json`) y pointer `ml_artifacts/champion.json`.
- `model.version` y `run_id` que devuelve la API **vienen del runtime**
  (adapter `app/model_registry.py`), nunca hardcodeados.

## Prediction logs

Cada request de forecast se registra en `metadata.prediction_logs`
(Postgres) con `id_pozo`, `periodo_mes`, predicción, versión de modelo,
`run_id` y timestamp. Detalle del lado API en manos del Integrante 2.

## Comandos de referencia

```bash
python -m ml.build_features --as-of-date 2026-06-01
python -m ml.train --as-of-date 2026-06-01
python -m ml.promotion_gate --candidate-run-id <run_id>
python -m ml.validate --model-alias champion
./scripts/retrain-model.sh 2026-06-01
```
