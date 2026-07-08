# Entrenamiento, validación y promoción

Flujo: `build_features -> train -> promotion_gate`, orquestado por Dagster
(`ml_training_job`, schedule mensual `ml_retraining_monthly`) o a mano con
`./scripts/retrain-model.sh [AS_OF_DATE]`.

## Entrenamiento

```bash
python -m ml.train --as-of-date 2026-06-01
```

- Modelo: `HistGradientBoostingRegressor` (sklearn) con one-hot de
  categóricas; tolera NaN en lags de pozos con poca historia.
- Split temporal (contrato): últimos 6 meses a test, o 3 si la historia no
  alcanza; sin solapamiento ni shuffle.
- Baseline: `prod_pet_lag_1`. Modelo y baseline se evalúan sobre las mismas
  filas de test; métricas: `mae` (primaria del gate), `rmse`, `smape`.
- En el **mismo run** se calculan las `feature_reference_stats` del set de
  entrenamiento y se insertan en Postgres (así el drift check nunca queda
  sin referencia).
- Artefactos locales: `ml_artifacts/runs/<run_id>/` con `model.pkl` y
  `metrics.json`. Si `MLFLOW_TRACKING_URI` está seteado, además se loguea
  el run en MLflow y se registra el modelo `oilgas_forecaster`.
  MLflow es la fuente primaria; el artefacto local es el fallback visible
  de sandbox.

## Gate de promoción

```bash
python -m ml.promotion_gate --candidate-run-id <run_id>
```

- **Bootstrap**: sin champion, promueve si el candidato supera al baseline.
- **Normal**: con champion, el candidato debe superar al baseline y al
  champion actual. El champion se re-evalúa sobre la misma ventana de test
  del candidato (comparación justa, no contra métricas viejas).
- Si promueve: actualiza `ml_artifacts/champion.json` y, si MLflow está
  disponible, mueve el alias `champion` a la versión del candidato.
- La decisión (promovido o no, con razón) se imprime como JSON y queda en
  `ml_artifacts/runs/<run_id>/gate_decision.json`. Exit 0 en ambos casos:
  "no promover" es una decisión válida, no un error.

## Validación del champion

```bash
python -m ml.validate --model-alias champion
```

Evalúa el champion vigente sobre el split temporal actual del feature
store y reporta modelo vs baseline. Exit 2 con mensaje claro si todavía no
hay champion promovido.

## Retraining para un día dado

- CLI: `./scripts/retrain-model.sh 2026-06-01`
- Dagster: lanzar `ml_training_job` desde el launchpad seteando
  `as_of_date` en la config de `build_features` y `train_model`. El
  schedule mensual (día 5, 07:00 ART) pasa la fecha de ejecución como
  `as_of_date` automáticamente.
