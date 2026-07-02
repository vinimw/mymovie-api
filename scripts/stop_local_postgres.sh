#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATA_DIR="${PROJECT_ROOT}/.postgres-data"

cd "${PROJECT_ROOT}"

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  docker compose stop postgres
  exit 0
fi

if [ -f "${DATA_DIR}/PG_VERSION" ]; then
  pg_ctl -D "${DATA_DIR}" stop
  exit 0
fi

echo "No local PostgreSQL instance managed by this project was found."
