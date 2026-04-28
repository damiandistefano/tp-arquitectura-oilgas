#!/usr/bin/env bash
# Smoke test de validación post-deploy en sandbox.
#
# Uso:
#   bash scripts/sandbox-smoke.sh <EC2_PUBLIC_IP>
#   bash scripts/sandbox-smoke.sh http://<EC2_PUBLIC_IP>
#
# Requiere que los puertos 8000, 9090, 9093 y 3000 estén abiertos en el Security Group.

set -euo pipefail

API_KEY="${API_KEY:-abcdef12345}"

if [[ $# -lt 1 ]]; then
  echo "Uso: $0 <EC2_PUBLIC_IP|BASE_URL>"
  exit 1
fi

INPUT_HOST="$1"

if [[ "${INPUT_HOST}" == http://* || "${INPUT_HOST}" == https://* ]]; then
  BASE_URL="${INPUT_HOST%/}"
else
  BASE_URL="http://${INPUT_HOST}"
fi

PASS=0
FAIL=0

check() {
  local desc="$1"
  local result="$2"

  if [[ "${result}" -eq 0 ]]; then
    echo "  ✓  ${desc}"
    PASS=$((PASS + 1))
  else
    echo "  ✗  ${desc}"
    FAIL=$((FAIL + 1))
  fi
}

run_check() {
  local desc="$1"
  shift

  if "$@" > /dev/null 2>&1; then
    check "${desc}" 0
  else
    check "${desc}" 1
  fi
}

echo ""
echo "=== Sandbox smoke test → ${BASE_URL} ==="
echo ""

# --- API (puerto 8000) ---
echo "[ API ]"

run_check "/health responde 200" \
  curl -fsS --max-time 5 "${BASE_URL}:8000/health"

run_check "/openapi.json responde 200" \
  curl -fsS --max-time 5 "${BASE_URL}:8000/openapi.json"

run_check "/metrics expone http_requests_total" \
  bash -c "curl -fsS --max-time 5 '${BASE_URL}:8000/metrics' | grep -q 'http_requests_total'"

run_check "/api/v1/wells con API key y date_query → 200" \
  curl -fsS --max-time 5 -H "X-API-Key: ${API_KEY}" \
    "${BASE_URL}:8000/api/v1/wells?date_query=2026-03-15"

run_check "/api/v1/forecast con API key → 200" \
  curl -fsS --max-time 5 -H "X-API-Key: ${API_KEY}" \
    "${BASE_URL}:8000/api/v1/forecast?id_well=POZO-001&date_start=2026-03-15&date_end=2026-03-20"

STATUS=$(curl -s --max-time 5 -o /dev/null -w "%{http_code}" \
  "${BASE_URL}:8000/api/v1/wells?date_query=2026-03-15" || true)

if [[ "${STATUS}" == "403" ]]; then
  check "/api/v1/wells sin API key → 403" 0
else
  echo "     status recibido: ${STATUS}"
  check "/api/v1/wells sin API key → 403" 1
fi

echo ""
echo "[ Prometheus ]"

run_check "Prometheus /-/healthy OK" \
  curl -fsS --max-time 5 "${BASE_URL}:9090/-/healthy"

run_check "Prometheus scrapea oilgas-api (health=up)" \
  bash -c "curl -fsS --max-time 5 '${BASE_URL}:9090/api/v1/targets' | grep -q '\"health\":\"up\"'"

RULES=$(curl -fsS --max-time 5 "${BASE_URL}:9090/api/v1/rules" 2>/dev/null || true)

echo "${RULES}" | grep -q "APIDown" && R=0 || R=1
check "Regla APIDown cargada" "${R}"

echo "${RULES}" | grep -q "HighErrorRate" && R=0 || R=1
check "Regla HighErrorRate cargada" "${R}"

echo "${RULES}" | grep -q "HighLatency" && R=0 || R=1
check "Regla HighLatency cargada" "${R}"

echo ""
echo "[ Alertmanager ]"

run_check "Alertmanager /-/healthy OK" \
  curl -fsS --max-time 5 "${BASE_URL}:9093/-/healthy"

echo ""
echo "[ Grafana ]"

run_check "Grafana /api/health OK" \
  bash -c "curl -fsS --max-time 5 '${BASE_URL}:3000/api/health' | grep -q '\"database\": \"ok\"'"

DS=$(curl -fsS --max-time 5 -u "admin:admin" "${BASE_URL}:3000/api/datasources" 2>/dev/null || true)

echo "${DS}" | grep -qi "prometheus" && R=0 || R=1
check "Datasource Prometheus provisionado" "${R}"

echo ""
echo "============================================"
echo "  Resultado: ${PASS} ✓   ${FAIL} ✗"
echo "============================================"
echo ""

[[ "${FAIL}" -eq 0 ]] && exit 0 || exit 1
