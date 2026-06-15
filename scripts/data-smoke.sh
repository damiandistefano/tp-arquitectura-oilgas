#!/usr/bin/env bash
set -euo pipefail

POSTGRES_USER="${POSTGRES_USER:-dwh}"
POSTGRES_DB="${POSTGRES_DB:-warehouse}"

query_scalar() {
  docker compose exec -T postgres psql \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    -v ON_ERROR_STOP=1 \
    -Atc "$1"
}

assert_count_positive() {
  local label="$1"
  local sql="$2"
  local count

  count="$(query_scalar "$sql")"
  echo "${label}: ${count}"

  if [ "${count}" -le 0 ]; then
    echo "Expected ${label} to have rows"
    exit 1
  fi
}

echo "Checking warehouse schemas..."
query_scalar "
  select count(*)
  from information_schema.schemata
  where schema_name in ('bronze', 'silver', 'gold', 'quality', 'metadata', 'semantic');
" | grep -qx "6"

echo "Checking medallion layers..."
assert_count_positive "bronze.raw_produccion_no_convencional" \
  "select count(*) from bronze.raw_produccion_no_convencional;"
assert_count_positive "bronze.raw_pozos_operadoras" \
  "select count(*) from bronze.raw_pozos_operadoras;"
assert_count_positive "metadata.source_files" \
  "select count(*) from metadata.source_files;"
assert_count_positive "silver.produccion_no_convencional" \
  "select count(*) from silver.produccion_no_convencional;"
assert_count_positive "silver.pozos_operadoras" \
  "select count(*) from silver.pozos_operadoras;"
assert_count_positive "gold.fact_produccion_pozo" \
  "select count(*) from gold.fact_produccion_pozo;"
assert_count_positive "semantic.vw_produccion_mensual" \
  "select count(*) from semantic.vw_produccion_mensual;"
assert_count_positive "quality.data_quality_results" \
  "select count(*) from quality.data_quality_results;"

echo "Checking critical quality failures..."
critical_failures="$(query_scalar "
  select count(*)
  from quality.data_quality_results
  where status = 'FAILED'
    and severity = 'CRITICAL';
")"
echo "critical quality failures: ${critical_failures}"

if [ "${critical_failures}" -gt 0 ]; then
  echo "Data smoke failed: there are critical quality failures"
  exit 1
fi

echo "Data smoke passed."
