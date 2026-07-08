#!/usr/bin/env bash
# Corre el drift check minimo contra el champion actual.
#
# Uso: ./scripts/run-drift-check.sh [AS_OF_DATE]
#   AS_OF_DATE en formato YYYY-MM-DD (default: hoy)
#
# Exit codes:
#   0 = sin drift
#   1 = drift detectado (revisar output)
#   2 = no se pudo evaluar (sin champion o sin reference stats)

set -euo pipefail

if command -v python >/dev/null 2>&1; then
  PYTHON_BIN="${PYTHON_BIN:-python}"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="${PYTHON_BIN:-python3}"
else
  echo "Python is required but was not found"
  exit 1
fi

AS_OF_DATE="${1:-$(date +%F)}"

echo "==> Drift check (as-of-date ${AS_OF_DATE})"
set +e
"$PYTHON_BIN" -m ml.drift_check --as-of-date "$AS_OF_DATE"
STATUS=$?
set -e

case "$STATUS" in
  0)
    echo "==> Drift check OK: sin drift"
    ;;
  1)
    echo "==> Drift check: drift detectado en una o mas features"
    ;;
  2)
    echo "==> Drift check no evaluado: falta champion o reference stats (ver mensaje arriba)"
    ;;
  *)
    echo "==> Drift check fallo con codigo inesperado ${STATUS}"
    ;;
esac

exit "$STATUS"
