#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

set -a
source ./.env
set +a

TEST_DB_NAME="${ODOO_TEST_DB_NAME:-test_digiplus_local}"
CRM_BOOTSTRAP_MODULES="digiplus_crm,l10n_cm"
CRM_TEST_TAGS="/digiplus_crm"
ACCOUNTING_TEMPLATE_CODE="${ODOO_ACCOUNTING_TEMPLATE_CODE:-cm}"
FINAL_MODULES="digiplus_agrochem_demo,digiplus_project"
FINAL_TEST_TAGS="/digiplus_agrochem_demo,/digiplus_project"

docker compose up -d --wait db

docker compose exec -T db bash -lc "
until psql -U \"${POSTGRES_USER}\" -d postgres -c 'SELECT 1;' >/dev/null 2>&1; do
    sleep 2
done

psql -U \"${POSTGRES_USER}\" -d postgres <<SQL
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '${TEST_DB_NAME}' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS ${TEST_DB_NAME};
SQL
"

echo "[1/3] Installation CRM DigiPlus et localisation comptable du Cameroun"
docker compose run --rm --no-deps odoo bash -lc "
odoo -c /etc/odoo/odoo.conf \
    -d ${TEST_DB_NAME} \
    -i ${CRM_BOOTSTRAP_MODULES} \
    --test-tags ${CRM_TEST_TAGS} \
    --stop-after-init
"

echo "[2/3] Initialisation du plan comptable local DigiPlus Consulting"
docker compose run --rm --no-deps odoo bash -lc "
cat >/tmp/bootstrap_local_accounting.py <<'PY'
company = env.company
cameroon = env.ref('base.cm', raise_if_not_found=False)

if cameroon and company.country_id != cameroon:
    company.country_id = cameroon

env['account.chart.template'].try_loading('${ACCOUNTING_TEMPLATE_CODE}', company, install_demo=True)
env.cr.commit()
env.invalidate_all()

print(
    'Configured accounting bootstrap for',
    company.name,
    'with',
    env['account.journal'].search_count([]),
    'journals and',
    env['account.account'].search_count([]),
    'accounts.',
)
PY
odoo shell -c /etc/odoo/odoo.conf -d ${TEST_DB_NAME} < /tmp/bootstrap_local_accounting.py
"

echo "[3/3] Installation et tests Ventes, Facturation et Projets"
docker compose run --rm --no-deps odoo bash -lc "
odoo -c /etc/odoo/odoo.conf \
    -d ${TEST_DB_NAME} \
    -i ${FINAL_MODULES} \
    --test-tags ${FINAL_TEST_TAGS} \
    --stop-after-init
"
