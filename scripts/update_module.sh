#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
set -a
source ./.env
set +a
MODULE_NAME="digiplus_agrochem_demo"
CUSTOM_MODULES="digiplus_crm,${MODULE_NAME}"
BASE_MODULES="crm,sale_management,contacts,mail,mass_mailing,stock,purchase,account,product,sale_stock,${MODULE_NAME}"

docker compose up -d db
docker compose stop odoo >/dev/null 2>&1 || true
docker compose rm -f odoo >/dev/null 2>&1 || true

docker compose run --rm --no-deps odoo bash -lc "odoo -c /etc/odoo/odoo.conf -d ${ODOO_DB_NAME} -i ${BASE_MODULES} --stop-after-init"
docker compose run --rm --no-deps odoo bash -lc "odoo -c /etc/odoo/odoo.conf -d ${ODOO_DB_NAME} -u ${CUSTOM_MODULES} --stop-after-init"

docker compose run --rm --no-deps odoo bash -lc "odoo shell -c /etc/odoo/odoo.conf -d ${ODOO_DB_NAME} <<'PY'
for module_name in ('marketing_automation', 'spreadsheet_dashboard'):
    module = env['ir.module.module'].search([('name', '=', module_name)], limit=1)
    if module and module.state not in ('installed', 'uninstallable'):
        module.button_immediate_install()
        print(f'{module_name} installed')
    else:
        print(f'{module_name} not available or already installed')
PY"

docker compose up -d odoo
