#!/usr/bin/env bash

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <previous-image-tag-or-commit-sha>"
  echo "Example: $0 4078096"
  exit 1
fi

ROLLBACK_TAG="$1"

echo "Starting rollback to image tag: ${ROLLBACK_TAG}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

IMAGE_TAG="${ROLLBACK_TAG}" "${SCRIPT_DIR}/deploy.sh"

echo "Rollback completed using image tag: ${ROLLBACK_TAG}"