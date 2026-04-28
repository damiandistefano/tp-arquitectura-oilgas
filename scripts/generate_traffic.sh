#!/usr/bin/env bash
# Genera tráfico sintético para poblar métricas en Prometheus/Grafana.
#
# Uso local:
#   bash scripts/generate_traffic.sh
#
# Uso contra EC2:
#   API=http://<EC2_PUBLIC_IP>:8000 bash scripts/generate_traffic.sh
#   API_URL=http://<EC2_PUBLIC_IP>:8000 bash scripts/generate_traffic.sh

set -euo pipefail

API="${API:-${API_URL:-http://localhost:8000}}"
KEY="${API_KEY:-abcdef12345}"

echo "Generando tráfico contra: ${API}"
echo ""

echo "[1/3] Generando 2xx (requests válidos)..."
for _ in {1..40}; do
  curl -s -H "X-API-Key: ${KEY}" \
    "${API}/api/v1/wells?date_query=2026-03-15" > /dev/null || true

  curl -s -H "X-API-Key: ${KEY}" \
    "${API}/api/v1/forecast?id_well=POZO-001&date_start=2026-03-15&date_end=2026-03-20" > /dev/null || true
done

echo "[2/3] Generando 4xx (sin API key)..."
for _ in {1..20}; do
  curl -s \
    "${API}/api/v1/wells?date_query=2026-03-15" > /dev/null || true
done

echo "[3/3] Generando 5xx (endpoint de debug)..."
for _ in {1..15}; do
  curl -s -H "X-API-Key: ${KEY}" \
    "${API}/api/v1/debug/fail" > /dev/null || true
done

echo ""
echo "Listo. Esperar ~20s y revisar Grafana/Prometheus."
