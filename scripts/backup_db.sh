#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
set -a
source ./.env
set +a
mkdir -p backups
STAMP="$(date +%Y%m%d_%H%M%S)"
docker compose exec -T db bash -lc "pg_dump -U ${POSTGRES_USER} ${ODOO_DB_NAME}" > "backups/${ODOO_DB_NAME}_${STAMP}.sql"
