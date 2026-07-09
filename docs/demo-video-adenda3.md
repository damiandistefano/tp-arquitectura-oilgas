# Demo video - Adenda 3 (ML Engineering)

Guion oficial del video obligatorio de Adenda 3. La demo muestra un flujo
integrado end-to-end sobre el mismo stack local.

## 1. Objetivo del video

Demostrar que el repo integra datos, ML y serving en un sistema operable:

- feature store offline en Postgres con grano `id_pozo + periodo_mes`;
- features sin leakage temporal;
- training batch comparado contra baseline naive;
- promotion gate que solo promueve si el candidato mejora;
- MLflow con experimento, registry y alias `champion`;
- API `/api/v1/forecast` con metadata runtime del modelo activo;
- prediction logs en `metadata.prediction_logs`;
- drift check desacoplado del serving;
- validacion con scripts y CI, no solo con capturas.

Duracion objetivo: 8 minutos.

| Bloque | Responsable | Tiempo |
|---|---|---|
| Intro general | I3 | 0:40 |
| Feature store, training y retraining | I1 | 2:30 |
| API predictiva, serving y prediction logs | I2 | 2:10 |
| MLflow, CI ML, drift y cierre | I3 | 2:40 |

## 2. Preparacion previa

El video arranca con el stack ya levantado y el pipeline corrido una vez.
Ejecutar desde la raiz del repo:

```bash
docker compose down -v
cp .env.example .env
pip install -r requirements-dev.txt
mkdir -p ml_artifacts
docker compose up --build -d postgres mlflow api dagster

set -a; . ./.env; set +a
bash scripts/mlflow-smoke.sh
bash scripts/data-ml-ci-smoke.sh
```

Notas:

- Dejar `MLFLOW_TRACKING_URI=` vacio en `.env`.
- Los contenedores usan `http://mlflow:5000` por default del Compose.
- Los scripts host exportan `http://localhost:5000`.
- Despues del cambio de MLflow, `docker compose down -v` es obligatorio al menos
  una vez para resetear el `artifact_location` viejo.
- En Windows, correr los scripts con Git Bash o un Bash equivalente con las
  dependencias Python instaladas.

Antes de grabar, verificar que el gate muestre `promoted=true` y que el curl de
forecast devuelva `model.source = "mlflow"`.

`scripts/validate-delivery.sh` levanta y baja su propio stack. No conviene
correrlo en vivo en medio del video porque destruye la demo; mostrar la salida
pregrabada o correrlo al final.

## 3. Guion minuto a minuto

| Minuto | Responsable | Que se muestra | Evidencia concreta | Comando / URL |
|---|---|---|---|---|
| 0:00-0:40 | I3 | Intro: sistema predictivo, arquitectura de datos + ML + serving | README | editor |
| 0:40-1:10 | I1 | Contrato ML: target `prod_pet`, grano `id_pozo + periodo_mes` | `docs/contracts.md` | editor |
| 1:10-1:50 | I1 | Feature store y no-leakage: lags/rolling usan meses anteriores | filas + codigo | `docker compose exec -T postgres psql -U dwh -d warehouse -c "select id_pozo, periodo_mes, prod_pet, prod_pet_lag_1, prod_pet_roll_mean_3 from features.pozo_monthly_features order by id_pozo, periodo_mes desc limit 6;"` |
| 1:50-2:40 | I1 | Training + baseline `prod_pet_lag_1` + promotion gate | JSON del gate | `python -m ml.build_features --as-of-date 2026-01-01`; `python -m ml.train --as-of-date 2026-01-01`; `python -m ml.promotion_gate --candidate-run-id "$(cat ml_artifacts/last_run_id.txt)"` |
| 2:40-3:10 | I1 | Retraining orquestado | Dagster UI con `ml_training_job` y `ml_retraining_monthly` | `http://localhost:3002` |
| 3:10-3:40 | I2 | Serving con adapter: MLflow primero, fallback local visible | ADR 0020 + `app/model_registry.py` | editor |
| 3:40-4:20 | I2 | Forecast model-backed en vivo | HTTP 200, predicciones y `source: "mlflow"` | `curl -s -H "X-API-Key: abcdef12345" "http://localhost:8000/api/v1/forecast?id_pozo=POZO-001&date_start=2026-01-01&date_end=2026-01-01" | jq` |
| 4:20-4:40 | I2 | Error controlado: pozo sin features | 404 claro, no 500 | `curl -s -H "X-API-Key: abcdef12345" "http://localhost:8000/api/v1/forecast?id_pozo=POZO-999&date_start=2026-01-01&date_end=2026-01-01" | jq` |
| 4:40-5:20 | I2 | Prediction logs | filas `success` y `error` | ver SELECT de seccion 4 |
| 5:20-6:00 | I3 | MLflow: run, modelo registrado y alias `champion` | MLflow UI | `http://localhost:5000` |
| 6:00-6:30 | I3 | CI de ML | `.github/workflows/ml-ci.yml` | GitHub Actions |
| 6:30-7:00 | I3 | Drift check minimo | JSON con z-score y `drifted` por feature | `bash scripts/run-drift-check.sh 2026-01-01` |
| 7:00-7:30 | I3 | Validacion de entrega | resumen PASS de `validate-delivery.sh` | salida pregrabada |
| 7:30-8:00 | I3 | Cierre: alcance y limitaciones | README + ADRs 0015-0023 | editor |

## 4. Flujo demo unico

Comandos puntuales para ejecutar en camara:

```bash
python -m ml.build_features --as-of-date 2026-01-01
python -m ml.train --as-of-date 2026-01-01
python -m ml.promotion_gate --candidate-run-id "$(cat ml_artifacts/last_run_id.txt)"
```

```bash
curl -s -H "X-API-Key: abcdef12345" \
  "http://localhost:8000/api/v1/forecast?id_pozo=POZO-001&date_start=2026-01-01&date_end=2026-01-01" | jq

curl -s -H "X-API-Key: abcdef12345" \
  "http://localhost:8000/api/v1/forecast?id_pozo=POZO-999&date_start=2026-01-01&date_end=2026-01-01" | jq
```

```bash
docker compose exec -T postgres psql -U dwh -d warehouse -c \
  "select prediction_id, requested_at, id_pozo, status, model_name, model_version, mlflow_run_id, model_source, latency_ms
   from metadata.prediction_logs order by requested_at desc limit 5;"
```

```bash
bash scripts/run-drift-check.sh 2026-01-01
```

Las fechas `2026-01-01` corresponden al ultimo mes del fixture
`tests/fixtures/ml_ci_fixture.sql`. Si se usa el pipeline con datos reales, elegir
un rango que exista en `features.pozo_monthly_features`.

## 5. Guion hablado resumido

**I1:** El contrato define target `prod_pet` y grano pozo-mes. Las features viven
en `features.pozo_monthly_features` y se generan con corte `as-of-date`: lags y
rolling usan solo meses anteriores. El entrenamiento batch compara un
HistGradientBoosting contra el baseline naive `prod_pet_lag_1`; el gate promueve
solo si mejora. El retraining mensual esta orquestado en Dagster con
`ml_training_job` y `ml_retraining_monthly`.

**I2:** La API expone `/api/v1/forecast` con `id_pozo`, `date_start` y
`date_end`. Para cada request busca features, resuelve el modelo activo por
MLflow alias `champion` y, si MLflow no esta disponible, cae a un fallback local
visible. El 200 muestra metadata runtime y `source: mlflow`. Cada request deja
evidencia en `metadata.prediction_logs`.

**I3:** MLflow corre como servicio local del Compose. El experimento tiene el run,
metricas y modelo registrado `oilgas_forecaster`; el alias `champion` apunta a la
version promovida. El workflow `ml-ci.yml` corre el mismo flujo sobre un fixture
chico. El drift check compara features recientes contra reference stats del
champion y reporta `drifted` por feature. El alcance AWS queda fuera para Adenda 3:
la demo model-backed se valida localmente.

## 6. Que no mostrar ni prometer

- No prometer sistema productivo: es un sandbox academico.
- No prometer que AWS cubre Adenda 3: `docker-compose.deploy.yml` no incluye
  Postgres ni MLflow.
- No prometer forecast futuro recursivo: el endpoint opera sobre periodos ya
  existentes en el feature store.
- No mostrar `.env`, `.pem`, tokens, credenciales ni configuraciones sensibles.
- No presentar `ml_artifacts/` como registry: es fallback local; MLflow es la
  fuente primaria de la demo.

## 7. Checklist pre-grabacion

- [ ] `ruff check .` pasa.
- [ ] `pytest -q` pasa.
- [ ] `docker compose config` pasa.
- [ ] Stack levantado desde cero con `docker compose down -v`.
- [ ] `bash scripts/mlflow-smoke.sh` pasa.
- [ ] `bash scripts/data-ml-ci-smoke.sh` completa con `promoted=true`.
- [ ] MLflow UI muestra experimento, modelo registrado y alias `champion`.
- [ ] Curl de forecast devuelve HTTP 200 con `"source": "mlflow"`.
- [ ] Curl de pozo inexistente devuelve 404 controlado.
- [ ] `metadata.prediction_logs` tiene al menos una fila `success` y una `error`.
- [ ] `bash scripts/run-drift-check.sh 2026-01-01` corre y muestra `drifted`.
- [ ] Salida de `bash scripts/validate-delivery.sh` guardada para mostrar.
- [ ] README, ADRs 0015-0023 y checklist de entrega actualizados.
- [ ] `git status` limpio, sin `.env`, `.pem`, `ml_artifacts/`, `mlruns/`, dumps ni `contexto/`.
