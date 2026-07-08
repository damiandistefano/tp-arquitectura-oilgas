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

# El fixture es chico y deterministico: el gate puede razonablemente NO
# promover si el candidato no supera al baseline naive (eso es el gate
# funcionando bien, no un bug). Lo unico que valida este paso es que la
# decision se haya calculado con la metrica primaria presente.
echo "$GATE_OUTPUT" | "$PYTHON_BIN" -c "
import json, sys
decision = json.load(sys.stdin)
assert 'promoted' in decision, 'el gate no devolvio una decision valida'
assert decision.get('candidate', {}).get('mae') is not None, 'el candidato no tiene metricas'
print(f\"==> Gate decidio promoted={decision['promoted']}: {decision['reason']}\")
"

echo "==> [6/6] API forecast smoke + prediction log + drift check"
CHECK_PREDICTION_LOGS=1 \
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
# dos es un resultado valido. exit 2 con status "no_champion" tambien es
# valido: en este fixture chico el gate puede no haber promovido nada
# todavia. Lo unico que es una falla real del smoke es exit 2 por
# no_reference_stats/no_recent_data: eso si indica un bug del pipeline.
if [ "$DRIFT_STATUS" -eq 2 ] && ! echo "$DRIFT_OUTPUT" | grep -q '"no_champion"'; then
  echo "==> data-ml-ci-smoke fallo: drift check no pudo evaluarse por un motivo inesperado"
  exit 1
fi

echo "==> data-ml-ci-smoke completado"
