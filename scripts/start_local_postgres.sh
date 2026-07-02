#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATA_DIR="${PROJECT_ROOT}/.postgres-data"
LOG_FILE="${PROJECT_ROOT}/postgres.log"

cd "${PROJECT_ROOT}"

if [ -f ".env" ]; then
  set -a
  . ".env"
  set +a
fi

POSTGRES_DB="${POSTGRES_DB:-my_movies}"
POSTGRES_USER="${POSTGRES_USER:-my_movies}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-my_movies}"
POSTGRES_PORT="${POSTGRES_PORT:-5433}"

print_database_url() {
  echo
  echo "DATABASE_URL=postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${POSTGRES_DB}"
}

start_with_docker() {
  echo "Starting local PostgreSQL with Docker Compose..."
  docker compose up -d postgres

  echo "Waiting for PostgreSQL to become healthy..."
  for _ in $(seq 1 30); do
    if docker compose exec -T postgres pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1; then
      echo "PostgreSQL is ready."
      print_database_url
      exit 0
    fi
    sleep 2
  done

  echo "PostgreSQL did not become ready in time." >&2
  exit 1
}

start_with_native_postgres() {
  echo "Docker daemon not available. Falling back to native PostgreSQL binaries..."

  if ! command -v initdb >/dev/null 2>&1 || ! command -v pg_ctl >/dev/null 2>&1 || ! command -v psql >/dev/null 2>&1; then
    echo "Native PostgreSQL binaries were not found. Install PostgreSQL or start Docker Desktop." >&2
    exit 1
  fi

  if [ ! -f "${DATA_DIR}/PG_VERSION" ]; then
    echo "Initializing native PostgreSQL data directory..."
    initdb -D "${DATA_DIR}" --username="${POSTGRES_USER}" --auth=trust >/dev/null
  fi

  if ! grep -q "include_if_exists = 'codex-local.conf'" "${DATA_DIR}/postgresql.conf"; then
    printf "\ninclude_if_exists = 'codex-local.conf'\n" >> "${DATA_DIR}/postgresql.conf"
  fi

  cat > "${DATA_DIR}/codex-local.conf" <<EOF
listen_addresses = '127.0.0.1'
port = ${POSTGRES_PORT}
unix_socket_directories = '${DATA_DIR}'
EOF

  if pg_ctl -D "${DATA_DIR}" status >/dev/null 2>&1; then
    echo "Native PostgreSQL is already running."
  else
    echo "Starting native PostgreSQL..."
    pg_ctl -D "${DATA_DIR}" -l "${LOG_FILE}" start >/dev/null
  fi

  echo "Waiting for native PostgreSQL to become ready..."
  for _ in $(seq 1 30); do
    if pg_isready -h 127.0.0.1 -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done

  psql \
    -h 127.0.0.1 \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d postgres \
    -v ON_ERROR_STOP=1 \
    --set=db_user="${POSTGRES_USER}" \
    --set=db_password="${POSTGRES_PASSWORD}" \
    --set=db_name="${POSTGRES_DB}" <<'SQL' >/dev/null
SELECT format('ALTER ROLE %I WITH LOGIN PASSWORD %L', :'db_user', :'db_password') \gexec
SELECT 'CREATE DATABASE ' || quote_ident(:'db_name')
WHERE NOT EXISTS (
  SELECT 1
  FROM pg_database
  WHERE datname = :'db_name'
) \gexec
SQL

  echo "Native PostgreSQL is ready."
  print_database_url
}

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  start_with_docker
else
  start_with_native_postgres
fi
