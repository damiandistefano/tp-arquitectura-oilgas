#!/usr/bin/env bash
# Pipeline ML end-to-end contra un fixture chico (sin datasets grandes):
#   fixture gold -> build_features -> no-leakage tests -> train ->
#   promotion_gate (bootstrap) -> API forecast smoke + prediction log ->
#   drift check.
#
# Pensado para correr local (con `docker compose up -d` ya levantado y
# las POSTGRES_*/API_* de .env exportadas) y para ser invocado desde CI
# (.github/workflows/ml-ci.yml) sin duplicar la logica del pipeline.
#
# Uso: ./scripts/data-ml-ci-smoke.sh [AS_OF_DATE]
#   AS_OF_DATE en formato YYYY-MM-DD (default: 2026-01-01, ultimo mes del fixture)

set -euo pipefail

if command -v python >/dev/null 2>&1; then
  PYTHON_BIN="${PYTHON_BIN:-python}"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="${PYTHON_BIN:-python3}"
else
  echo "Python is required but was not found"
  exit 1
fi

POSTGRES_USER="${POSTGRES_USER:-dwh}"
POSTGRES_DB="${POSTGRES_DB:-warehouse}"
AS_OF_DATE="${1:-2026-01-01}"
export MLFLOW_TRACKING_URI="${MLFLOW_TRACKING_URI:-http://localhost:5000}"
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"

echo "==> [1/6] Cargando fixture gold chico en Postgres"
docker compose exec -T postgres psql \
  -U "${POSTGRES_USER}" \
  -d "${POSTGRES_DB}" \
  -v ON_ERROR_STOP=1 \
  < tests/fixtures/ml_ci_fixture.sql

echo "==> [2/6] Generando features (as-of-date ${AS_OF_DATE})"
"$PYTHON_BIN" -m ml.build_features --as-of-date "$AS_OF_DATE"

echo "==> [3/6] Chequeo de no-leakage temporal (tests unitarios de features)"
"$PYTHON_BIN" -m pytest tests/test_ml_features.py -q

echo "==> [4/6] Entrenando modelo tiny sobre el fixture"
"$PYTHON_BIN" -m ml.train --as-of-date "$AS_OF_DATE"

ARTIFACTS_DIR="${ML_ARTIFACTS_DIR:-ml_artifacts}"
RUN_ID="$(cat "$ARTIFACTS_DIR/last_run_id.txt")"

echo "==> [5/6] Gate de promocion bootstrap (candidato ${RUN_ID})"
GATE_OUTPUT="$("$PYTHON_BIN" -m ml.promotion_gate --candidate-run-id "$RUN_ID")"
echo "$GATE_OUTPUT"

export GATE_OUTPUT
PROMOTED="$("$PYTHON_BIN" - <<'PY'
import json
import os
import sys

decision = json.loads(os.environ["GATE_OUTPUT"])
assert "promoted" in decision, "el gate no devolvio una decision valida"
assert decision.get("candidate", {}).get("mae") is not None, "el candidato no tiene metricas"
print(
    f"==> Gate decidio promoted={decision['promoted']}: {decision['reason']}",
    file=sys.stderr,
)
assert decision["promoted"] is True, "el fixture ML debe promover al candidato"
print("1")
PY
)"

if [ "$PROMOTED" = "1" ] && [ -n "${MLFLOW_TRACKING_URI:-}" ]; then
  "$PYTHON_BIN" - <<'PY'
import os

import mlflow

tracking_uri = os.environ["MLFLOW_TRACKING_URI"]
model_name = os.getenv("MLFLOW_MODEL_NAME", "oilgas_forecaster")
alias = os.getenv("MLFLOW_MODEL_ALIAS", "champion")
client = mlflow.MlflowClient(tracking_uri=tracking_uri)
version = client.get_model_version_by_alias(model_name, alias)
print(
    f"==> Alias MLflow verificado: {model_name}@{alias} "
    f"-> version={version.version}, run_id={version.run_id}"
)
PY
fi

echo "==> [6/6] API forecast smoke + prediction log + drift check"
if [ "$PROMOTED" = "1" ]; then
  EXPECTED_MODEL_SOURCE_VALUE="mlflow"
else
  EXPECTED_MODEL_SOURCE_VALUE=""
fi

CHECK_PREDICTION_LOGS=1 \
  REQUIRE_200=1 \
  EXPECTED_MODEL_SOURCE="${EXPECTED_MODEL_SOURCE_VALUE}" \
  ID_POZO="${ID_POZO:-POZO-001}" \
  DATE_START="${DATE_START:-2026-01-01}" \
  DATE_END="${DATE_END:-2026-01-01}" \
  bash scripts/api-forecast-smoke.sh

set +e
DRIFT_OUTPUT="$(bash scripts/run-drift-check.sh "$AS_OF_DATE")"
DRIFT_STATUS=$?
set -e
echo "$DRIFT_OUTPUT"

# exit 0/1 (ok/drift_detected) = evaluo correctamente, cualquiera de los
# dos es un resultado valido. exit 2 indica que el drift check no pudo
# usar el champion promovido y eso bloquea el smoke integrado.
if [ "$DRIFT_STATUS" -eq 2 ]; then
  echo "==> data-ml-ci-smoke fallo: drift check no pudo evaluarse"
  exit 1
fi

echo "==> data-ml-ci-smoke completado"
