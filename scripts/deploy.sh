#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$HOME/tp-arquitectura-oilgas}"
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

echo "Pulling image from GHCR..."
docker compose -f "${COMPOSE_FILE}" pull

echo "Starting API service..."
docker compose -f "${COMPOSE_FILE}" up -d

echo "Running post-deploy health check..."
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

echo "Current running containers:"
docker compose -f "${COMPOSE_FILE}" ps