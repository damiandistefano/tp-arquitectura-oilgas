#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

PROJECT_DIR="${PROJECT_DIR:-${DEFAULT_PROJECT_DIR}}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.deploy.yml}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
API_PORT="${API_PORT:-8000}"
HEALTHCHECK_URL="${HEALTHCHECK_URL:-http://localhost:${API_PORT}/openapi.json}"

export IMAGE_TAG
export API_PORT

echo "Deploy configuration:"
echo "- PROJECT_DIR=${PROJECT_DIR}"
echo "- COMPOSE_FILE=${COMPOSE_FILE}"
echo "- IMAGE_TAG=${IMAGE_TAG}"
echo "- API_PORT=${API_PORT}"
echo "- HEALTHCHECK_URL=${HEALTHCHECK_URL}"

cd "${PROJECT_DIR}"

if [ ! -f "${COMPOSE_FILE}" ]; then
  echo "ERROR: Compose file not found: ${COMPOSE_FILE}"
  exit 1
fi

GRAFANA_PORT="${GRAFANA_PORT:-3000}"
GRAFANA_HEALTHCHECK_URL="${GRAFANA_HEALTHCHECK_URL:-http://localhost:${GRAFANA_PORT}/api/health}"

echo "Pulling API image from GHCR..."
docker compose -f "${COMPOSE_FILE}" pull api

echo "Building monitoring services (prometheus, grafana, alertmanager)..."
docker compose -f "${COMPOSE_FILE}" build prometheus grafana alertmanager

echo "Starting all services..."
docker compose -f "${COMPOSE_FILE}" up -d

echo "Running post-deploy health checks..."
API_UP=false
for i in {1..20}; do
  if curl -fsS "${HEALTHCHECK_URL}" > /dev/null; then
    echo "Deploy OK: API is healthy."
    API_UP=true
    break
  fi
  echo "API not ready yet. Retry ${i}/20..."
  sleep 3
done

if [ "${API_UP}" != "true" ]; then
  echo "ERROR: API did not become healthy after deploy."
  docker compose -f "${COMPOSE_FILE}" logs api || true
  exit 1
fi

GRAFANA_UP=false
for i in {1..15}; do
  if curl -fsS "${GRAFANA_HEALTHCHECK_URL}" > /dev/null 2>&1; then
    echo "Deploy OK: Grafana is healthy."
    GRAFANA_UP=true
    break
  fi
  echo "Grafana not ready yet. Retry ${i}/15..."
  sleep 3
done

if [ "${GRAFANA_UP}" != "true" ]; then
  echo "WARNING: Grafana did not become healthy after deploy. Check port 3000 and logs."
  docker compose -f "${COMPOSE_FILE}" logs grafana || true
fi

echo "Current running containers:"
docker compose -f "${COMPOSE_FILE}" ps