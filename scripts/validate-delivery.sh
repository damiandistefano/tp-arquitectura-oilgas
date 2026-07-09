#!/usr/bin/env bash
# Orquestador final de entrega de Adenda 3: corre el checklist completo
# (config, lint, tests, stack real, MLflow, pipeline ML con fixture y
# Dagster) y termina con un resumen PASS/FAIL por paso.
#
# Uso: bash scripts/validate-delivery.sh
# Requiere: docker, docker compose, python con requirements-dev.txt
# instalado. Levanta y baja su propio stack de docker compose.

set -uo pipefail

if command -v python >/dev/null 2>&1; then
  PYTHON_BIN="${PYTHON_BIN:-python}"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="${PYTHON_BIN:-python3}"
else
  echo "Python is required but was not found"
  exit 1
fi

RESULTS=()

step() {
  local label="$1"
  shift
  echo ""
  echo "=== ${label} ==="
  if "$@"; then
    RESULTS+=("PASS  ${label}")
  else
    RESULTS+=("FAIL  ${label}")
  fi
}

cleanup() {
  docker compose down -v > /dev/null 2>&1 || true
}
trap cleanup EXIT

cp -n .env.example .env 2>/dev/null || true

# Los pasos que corren python fuera de docker (build_features/train/gate)
# necesitan conectarse a postgres como lo hace el host, no como dagster:
# localhost:5433 (ver .env.example), no postgres:5432.
export POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
export POSTGRES_PORT="${POSTGRES_PORT:-5433}"
export POSTGRES_USER="${POSTGRES_USER:-dwh}"
export POSTGRES_DB="${POSTGRES_DB:-warehouse}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-dwh}"
export API_KEY="${API_KEY:-abcdef12345}"
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"

step "docker compose config" docker compose config
step "ruff check" ruff check .
step "pytest" "$PYTHON_BIN" -m pytest -q

step "levantar postgres + mlflow + api + dagster" \
  docker compose up -d --build postgres mlflow api dagster

step "mlflow smoke" bash scripts/mlflow-smoke.sh
step "pipeline ML con fixture chico" bash scripts/data-ml-ci-smoke.sh
step "dagster tiene ml_training_job + schedule mensual" bash -c '
  OUTPUT="$(MSYS_NO_PATHCONV=1 docker compose exec -T -e DAGSTER_HOME=/tmp/dagster_home dagster \
    sh -c "mkdir -p \$DAGSTER_HOME \
      && dagster job list -m dwh_pipeline.definitions \
      && dagster schedule list -m dwh_pipeline.definitions")"
  echo "$OUTPUT"
  echo "$OUTPUT" | grep -q ml_training_job && echo "$OUTPUT" | grep -q ml_retraining_monthly
'

echo ""
echo "=== Resumen ==="
FAILED=0
for line in "${RESULTS[@]}"; do
  echo "${line}"
  case "${line}" in
    FAIL*) FAILED=1 ;;
  esac
done

if [ "${FAILED}" -eq 1 ]; then
  echo ""
  echo "validate-delivery: hay pasos en FAIL, revisar arriba."
  exit 1
fi

echo ""
echo "validate-delivery: todo OK."
