# Serving de inferencia forecast

El endpoint predictivo de Adenda 3 es:

```text
GET /api/v1/forecast?id_pozo=POZO-001&date_start=2026-01-01&date_end=2026-01-01
```

Requiere header:

```http
X-API-Key: abcdef12345
```

La respuesta publica usa `id_pozo`, target mensual `prod_pet`, horizonte
`YYYY-MM`, predicciones por `periodo_mes` y metadata runtime del modelo:

```json
{
  "id_pozo": "POZO-001",
  "target": "prod_pet",
  "horizon": ["2026-07"],
  "predictions": [
    {"periodo_mes": "2026-07", "prediction": 123.4}
  ],
  "model": {
    "name": "oilgas_forecaster",
    "version": "<runtime>",
    "alias": "champion",
    "run_id": "<runtime>",
    "source": "mlflow"
  }
}
```

## Flujo

1. `app/api.py` valida API key y fechas.
2. `app/feature_lookup.py` lee `features.pozo_monthly_features` en Postgres.
3. `app/model_registry.py` intenta usar MLflow cuando `MLFLOW_TRACKING_URI`
   esta configurado y la dependencia esta disponible.
4. Si MLflow no esta disponible, usa artifact local o fallback local visible
   con `model.source = "local_fallback"`.
5. `app/ml_inference.py` ejecuta `predict` y normaliza la salida mensual.
6. `app/prediction_logging.py` intenta registrar la inferencia en
   `metadata.prediction_logs`.

## Variables utiles

```env
MLFLOW_TRACKING_URI=http://mlflow:5000
MLFLOW_MODEL_NAME=oilgas_forecaster
MLFLOW_MODEL_ALIAS=champion
ML_ARTIFACTS_DIR=ml_artifacts
LOCAL_MODEL_FALLBACK_PATH=
LOCAL_MODEL_FALLBACK_ENABLED=true
```

El fallback local es para sandbox/demo. No se oculta como MLflow: la respuesta
y los logs guardan `model_source = local_fallback`.

Para servir artifacts sklearn locales, la imagen de API instala las
dependencias minimas de serving (`pandas`, `scikit-learn`, `joblib`) y monta
`ml_artifacts` como solo lectura en `/app/ml_artifacts`.

## Errores

| HTTP | Caso |
|---|---|
| `400` | rango de fechas invalido |
| `404` | pozo sin features o rango sin features |
| `503` | tabla de features no disponible, schema incompatible o modelo no disponible |
| `500` | error inesperado no clasificado |

## Prediction logs

Cada request con fechas validas intenta insertar un registro en:

```text
metadata.prediction_logs
```

El log guarda `id_pozo`, rango, target, metadata del modelo, cantidad de
predicciones, estado, error si aplica, latencia, payload sanitizado y resumen
de respuesta. No guarda API keys ni headers sensibles.

Si falla el logging, la API registra un warning. Un forecast exitoso no se
convierte en error solo porque Postgres no pudo escribir el log.

## Smoke test

```bash
bash scripts/api-forecast-smoke.sh
```

Para la demo final, el endpoint deberia responder `200` con features y
modelo/fallback disponibles. El script acepta un `404` o `503` controlado solo
como senal de integracion parcial: faltan features en Postgres o modelo activo,
pero la API y el contrato ya son alcanzables.

## Limitacion explicita

El forecast mensual model-backed opera sobre periodos existentes en
`features.pozo_monthly_features`. La generacion recursiva de meses futuros queda
fuera de alcance de esta entrega.
