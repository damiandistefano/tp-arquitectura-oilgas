#!/usr/bin/env bash
# Smoke test puntual del endpoint model-backed de forecast.

set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
API_KEY="${API_KEY:-abcdef12345}"
ID_POZO="${ID_POZO:-POZO-001}"
DATE_START="${DATE_START:-2026-01-01}"
DATE_END="${DATE_END:-2026-01-01}"
REQUIRE_200="${REQUIRE_200:-0}"
EXPECTED_MODEL_SOURCE="${EXPECTED_MODEL_SOURCE:-}"
FORECAST_MAX_TIME_SECONDS="${FORECAST_MAX_TIME_SECONDS:-60}"

TMP_RESPONSE="$(mktemp)"
trap 'rm -f "${TMP_RESPONSE}"' EXIT

echo "== API forecast smoke =="
echo "API_URL=${API_URL}"
echo "ID_POZO=${ID_POZO}"
echo "DATE_START=${DATE_START}"
echo "DATE_END=${DATE_END}"
echo ""

curl -fsS --max-time 5 "${API_URL}/health" > /dev/null
echo "OK /health"

curl -fsS --max-time 5 "${API_URL}/openapi.json" > /dev/null
echo "OK /openapi.json"

FORECAST_URL="${API_URL}/api/v1/forecast?id_pozo=${ID_POZO}&date_start=${DATE_START}&date_end=${DATE_END}"
STATUS="$(
  curl -sS --max-time "${FORECAST_MAX_TIME_SECONDS}" \
    -o "${TMP_RESPONSE}" \
    -w "%{http_code}" \
    -H "X-API-Key: ${API_KEY}" \
    "${FORECAST_URL}" || true
)"

if [[ "${STATUS}" == "200" ]]; then
  python - "${TMP_RESPONSE}" "${ID_POZO}" "${EXPECTED_MODEL_SOURCE}" <<'PY'
import json
import sys

path, expected_id, expected_source = sys.argv[1], sys.argv[2], sys.argv[3]
body = json.loads(open(path, encoding="utf-8").read())

assert body["id_pozo"] == expected_id
assert body["target"] == "prod_pet"
assert isinstance(body["horizon"], list)
assert isinstance(body["predictions"], list)
assert body["model"]["name"]
assert body["model"]["version"]
assert body["model"]["run_id"]
assert body["model"]["source"] in {"mlflow", "local_fallback"}
if expected_source:
    assert body["model"]["source"] == expected_source, (
        f"model.source esperado {expected_source!r}, "
        f"recibido {body['model']['source']!r}"
    )
PY
  echo "OK /api/v1/forecast contrato id_pozo + metadata runtime"
elif [[ "${STATUS}" == "404" || "${STATUS}" == "503" ]]; then
  if [[ "${REQUIRE_200}" == "1" ]]; then
    echo "ERROR /api/v1/forecast respondio ${STATUS} y REQUIRE_200=1"
    cat "${TMP_RESPONSE}"
    echo ""
    exit 1
  fi
  echo "WARN /api/v1/forecast respondio ${STATUS}: endpoint alcanzable con precondicion faltante"
  echo "Esto es aceptable si aun no hay features en Postgres o modelo activo/fallback disponible."
  cat "${TMP_RESPONSE}"
  echo ""
else
  echo "ERROR /api/v1/forecast status inesperado: ${STATUS}"
  cat "${TMP_RESPONSE}"
  echo ""
  exit 1
fi

if [[ "${CHECK_PREDICTION_LOGS:-0}" == "1" ]]; then
  docker compose exec -T postgres psql \
    -U "${POSTGRES_USER:-dwh}" \
    -d "${POSTGRES_DB:-warehouse}" \
    -c "select prediction_id, requested_at, id_pozo, status, model_source from metadata.prediction_logs order by requested_at desc limit 5;"
fi
