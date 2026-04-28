#!/bin/bash
set -e

API="${API:-http://localhost:8000}"
KEY="${API_KEY:-abcdef12345}"

echo "Generando 2xx (requests validos)..."
for i in {1..40}; do
  curl -s -H "X-API-Key: $KEY" "$API/api/v1/wells?date_query=2024-01-01" > /dev/null
  curl -s -H "X-API-Key: $KEY" "$API/api/v1/forecast?id_well=POZO-001&date_start=2024-01-01&date_end=2024-01-31" > /dev/null
done

echo "Generando 4xx (sin API key)..."
for i in {1..20}; do
  curl -s "$API/api/v1/wells?date_query=2024-01-01" > /dev/null
done

echo "Generando 5xx (endpoint de debug)..."
for i in {1..15}; do
  curl -s -H "X-API-Key: $KEY" "$API/api/v1/debug/fail" > /dev/null
done

echo "Listo. Esperar ~20s y revisar Grafana."
