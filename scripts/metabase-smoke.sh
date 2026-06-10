#!/usr/bin/env bash
set -euo pipefail

echo "Checking Metabase health..."
curl -f http://localhost:3001/api/health

echo "Checking BI semantic views..."
docker compose exec -T postgres psql -U dwh -d warehouse -c "select count(*) from semantic.vw_produccion_mensual;"
docker compose exec -T postgres psql -U dwh -d warehouse -c "select count(*) from semantic.vw_produccion_por_operadora;"
docker compose exec -T postgres psql -U dwh -d warehouse -c "select count(*) from semantic.vw_produccion_por_area;"
docker compose exec -T postgres psql -U dwh -d warehouse -c "select count(*) from semantic.vw_frescura_datos;"

echo "Checking quality results..."
docker compose exec -T postgres psql -U dwh -d warehouse -c "select status, count(*) from quality.data_quality_results group by status;"

echo "Metabase BI smoke test passed."