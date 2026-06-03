#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "Usage: bash scripts/backfill.sh <start_date> [end_date]"
  exit 1
fi

start_date="$1"
end_date="${2:-$1}"

echo "Backfill requested from ${start_date} to ${end_date}"
