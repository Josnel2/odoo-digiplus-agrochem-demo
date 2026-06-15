#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
set -a
source ./.env
set +a

docker compose up -d db
docker compose exec -T db bash -lc "psql -U ${POSTGRES_USER} -d postgres -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${ODOO_DB_NAME}' AND pid <> pg_backend_pid();\" >/dev/null"
docker compose exec -T db bash -lc "psql -U ${POSTGRES_USER} -d postgres -c \"DROP DATABASE IF EXISTS ${ODOO_DB_NAME};\""
"$ROOT_DIR/scripts/update_module.sh"
