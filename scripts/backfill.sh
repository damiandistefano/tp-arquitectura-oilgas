#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "Usage: bash scripts/backfill.sh <start_date> [end_date]"
  echo "Dates must use YYYY-MM-DD format."
  exit 1
fi

start_date="$1"
end_date="${2:-$1}"

if ! [[ "${start_date}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
  echo "Invalid start_date: ${start_date}. Expected YYYY-MM-DD."
  exit 1
fi

if ! [[ "${end_date}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
  echo "Invalid end_date: ${end_date}. Expected YYYY-MM-DD."
  exit 1
fi

if command -v python >/dev/null 2>&1; then
  PYTHON_BIN="${PYTHON_BIN:-python}"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="${PYTHON_BIN:-python3}"
else
  echo "Python is required but was not found"
  exit 1
fi

if ! command -v dbt >/dev/null 2>&1; then
  echo "dbt is required but was not found"
  echo "Install development dependencies with: python -m pip install -r requirements-dev.txt"
  exit 1
fi

export POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
export POSTGRES_PORT="${POSTGRES_PORT:-5433}"
export POSTGRES_DB="${POSTGRES_DB:-warehouse}"
export POSTGRES_USER="${POSTGRES_USER:-dwh}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-dwh}"

echo "Backfill requested from ${start_date} to ${end_date}"
echo "This project uses full public CSV downloads. The backfill rebuilds downstream models and quality checks for all available periods, including the requested range."

echo "Refreshing Bronze from source files..."
"${PYTHON_BIN}" -m extract.load_to_bronze

echo "Rebuilding dbt models..."
dbt build --project-dir dbt

echo "Running quality checks..."
"${PYTHON_BIN}" -m quality.checks

echo "Backfill completed from ${start_date} to ${end_date}"
