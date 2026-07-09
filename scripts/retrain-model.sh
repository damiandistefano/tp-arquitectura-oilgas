#!/usr/bin/env bash
set -euo pipefail

# Reentrenamiento end-to-end para un día dado:
#   features -> training (+ reference stats) -> gate de promoción.
# Correr desde la raíz del repo con las POSTGRES_* de .env exportadas.
#
# Uso: ./scripts/retrain-model.sh [AS_OF_DATE]
#   AS_OF_DATE en formato YYYY-MM-DD (default: hoy)

if command -v python >/dev/null 2>&1; then
  PYTHON_BIN="${PYTHON_BIN:-python}"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="${PYTHON_BIN:-python3}"
else
  echo "Python is required but was not found"
  exit 1
fi

AS_OF_DATE="${1:-$(date +%F)}"
ARTIFACTS_DIR="${ML_ARTIFACTS_DIR:-ml_artifacts}"
export MLFLOW_TRACKING_URI="${MLFLOW_TRACKING_URI:-http://localhost:5000}"
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"

echo "==> [1/3] Generando features (as-of-date ${AS_OF_DATE})"
"$PYTHON_BIN" -m ml.build_features --as-of-date "$AS_OF_DATE"

echo "==> [2/3] Entrenando modelo"
"$PYTHON_BIN" -m ml.train --as-of-date "$AS_OF_DATE"

RUN_ID="$(cat "$ARTIFACTS_DIR/last_run_id.txt")"

echo "==> [3/3] Gate de promoción (candidato ${RUN_ID})"
"$PYTHON_BIN" -m ml.promotion_gate --candidate-run-id "$RUN_ID"

echo "==> Retraining completado"
