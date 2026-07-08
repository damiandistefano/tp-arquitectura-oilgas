#!/usr/bin/env bash
# Smoke test del servicio MLflow (tracking + registry).
#
# Uso: bash scripts/mlflow-smoke.sh
# Requiere el stack levantado: docker compose up -d mlflow

set -euo pipefail

MLFLOW_URL="${MLFLOW_URL:-http://localhost:5000}"

echo "== MLflow smoke =="
echo "MLFLOW_URL=${MLFLOW_URL}"

curl -fsS --max-time 5 "${MLFLOW_URL}/health" > /dev/null
echo "OK /health"

curl -fsS --max-time 5 "${MLFLOW_URL}/" > /dev/null
echo "OK / (UI de tracking)"

curl -fsS --max-time 5 -X GET \
  "${MLFLOW_URL}/api/2.0/mlflow/experiments/search?max_results=1" \
  -H "Content-Type: application/json" > /dev/null
echo "OK /api/2.0/mlflow/experiments/search"

echo "MLflow smoke passed."
