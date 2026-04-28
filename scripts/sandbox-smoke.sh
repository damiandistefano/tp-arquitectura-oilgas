#!/usr/bin/env bash
# Smoke test de validación post-deploy en sandbox.
# Uso: ./scripts/sandbox-smoke.sh <EC2_PUBLIC_IP>
# Requiere que los puertos 8000, 9090 y 9093 estén abiertos en el SG.

set -euo pipefail

API_KEY="abcdef12345"

if [[ $# -lt 1 ]]; then
  echo "Uso: $0 <EC2_PUBLIC_IP>"
  exit 1
fi

HOST="$1"
PASS=0
FAIL=0

check() {
  local desc="$1"
  local result="$2"  # 0 = ok
  if [[ "$result" -eq 0 ]]; then
    echo "  ✓  $desc"
    PASS=$((PASS + 1))
  else
    echo "  ✗  $desc"
    FAIL=$((FAIL + 1))
  fi
}

echo ""
echo "=== Sandbox smoke test → http://${HOST} ==="
echo ""

# --- API (puerto 8000) ---
echo "[ API ]"

curl -fsS --max-time 5 "http://${HOST}:8000/health" -o /dev/null 2>&1
check "/health responde 200" $?

curl -fsS --max-time 5 "http://${HOST}:8000/openapi.json" -o /dev/null 2>&1
check "/openapi.json responde 200" $?

curl -fsS --max-time 5 "http://${HOST}:8000/metrics" 2>/dev/null | grep -q "http_requests_total"
check "/metrics expone http_requests_total" $?

curl -fsS --max-time 5 -H "X-API-Key: ${API_KEY}" "http://${HOST}:8000/api/v1/wells" -o /dev/null 2>&1
check "/api/v1/wells con API key → 200" $?

# 401 sin API key (curl devuelve no-zero en 4xx con -f, lo esperamos)
STATUS=$(curl -s --max-time 5 -o /dev/null -w "%{http_code}" "http://${HOST}:8000/api/v1/wells")
[[ "$STATUS" == "401" || "$STATUS" == "403" ]] && R=0 || R=1
check "/api/v1/wells sin API key → 401/403 (got $STATUS)" $R

echo ""
echo "[ Prometheus ]"

curl -fsS --max-time 5 "http://${HOST}:9090/-/healthy" -o /dev/null 2>&1
check "Prometheus /-/healthy OK" $?

curl -fsS --max-time 5 "http://${HOST}:9090/api/v1/targets" 2>/dev/null | grep -q '"health":"up"'
check "Prometheus scrapea oilgas-api (health=up)" $?

RULES=$(curl -fsS --max-time 5 "http://${HOST}:9090/api/v1/rules" 2>/dev/null)
echo "$RULES" | grep -q "APIDown" && R=0 || R=1
check "Regla APIDown cargada" $R
echo "$RULES" | grep -q "HighErrorRate" && R=0 || R=1
check "Regla HighErrorRate cargada" $R

echo ""
echo "[ Alertmanager ]"

curl -fsS --max-time 5 "http://${HOST}:9093/-/healthy" -o /dev/null 2>&1
check "Alertmanager /-/healthy OK" $?

echo ""
echo "[ Grafana ]"

curl -fsS --max-time 5 "http://${HOST}:3000/api/health" 2>/dev/null | grep -q '"database": "ok"'
check "Grafana /api/health OK" $?

# Datasource Prometheus configurado
DS=$(curl -fsS --max-time 5 -u "admin:admin" "http://${HOST}:3000/api/datasources" 2>/dev/null)
echo "$DS" | grep -qi "prometheus" && R=0 || R=1
check "Datasource Prometheus provisionado" $R

echo ""
echo "============================================"
echo "  Resultado: ${PASS} ✓   ${FAIL} ✗"
echo "============================================"
echo ""

[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
