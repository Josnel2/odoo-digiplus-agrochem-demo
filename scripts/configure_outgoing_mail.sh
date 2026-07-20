#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

set -a
source ./.env
set +a

DB_NAME="${1:-${ODOO_DB_NAME:-}}"
SMTP_NAME="${DIGIPLUS_SMTP_NAME:-DigiPlus SMTP}"
SMTP_FROM_NAME="${DIGIPLUS_SMTP_FROM_NAME:-Odoo DigiPlus}"
SMTP_HOST="${DIGIPLUS_SMTP_HOST:-}"
SMTP_PORT="${DIGIPLUS_SMTP_PORT:-587}"
SMTP_USER="${DIGIPLUS_SMTP_USER:-}"
SMTP_PASSWORD="${DIGIPLUS_SMTP_PASSWORD:-}"
SMTP_ENCRYPTION="${DIGIPLUS_SMTP_ENCRYPTION:-starttls}"
SMTP_FROM_FILTER="${DIGIPLUS_SMTP_FROM_FILTER:-}"
COMPANY_EMAIL="${DIGIPLUS_COMPANY_EMAIL:-}"
ALIAS_DOMAIN="${DIGIPLUS_ALIAS_DOMAIN:-}"
DEFAULT_FROM_ALIAS="${DIGIPLUS_DEFAULT_FROM_ALIAS:-notifications}"
CATCHALL_ALIAS="${DIGIPLUS_CATCHALL_ALIAS:-catchall}"
BOUNCE_ALIAS="${DIGIPLUS_BOUNCE_ALIAS:-bounce}"

if [[ -z "$DB_NAME" ]]; then
    echo "ODOO_DB_NAME is not defined and no database was passed as argument." >&2
    exit 1
fi

for required_var in SMTP_HOST SMTP_USER SMTP_PASSWORD SMTP_FROM_FILTER; do
    if [[ -z "${!required_var}" ]]; then
        echo "$required_var is required. Set DIGIPLUS_${required_var} in .env." >&2
        exit 1
    fi
done

case "$SMTP_ENCRYPTION" in
    none|starttls|ssl)
        ;;
    *)
        echo "DIGIPLUS_SMTP_ENCRYPTION must be one of: none, starttls, ssl" >&2
        exit 1
        ;;
esac

docker compose up -d db odoo >/dev/null

for _ in {1..30}; do
    if docker compose exec -T odoo true >/dev/null 2>&1; then
        break
    fi
    sleep 2
done

if ! docker compose exec -T odoo true >/dev/null 2>&1; then
    echo "Odoo container is not ready." >&2
    exit 1
fi

docker compose exec -T \
    -e DIGIPLUS_SMTP_NAME="$SMTP_NAME" \
    -e DIGIPLUS_SMTP_FROM_NAME="$SMTP_FROM_NAME" \
    -e DIGIPLUS_SMTP_HOST="$SMTP_HOST" \
    -e DIGIPLUS_SMTP_PORT="$SMTP_PORT" \
    -e DIGIPLUS_SMTP_USER="$SMTP_USER" \
    -e DIGIPLUS_SMTP_PASSWORD="$SMTP_PASSWORD" \
    -e DIGIPLUS_SMTP_ENCRYPTION="$SMTP_ENCRYPTION" \
    -e DIGIPLUS_SMTP_FROM_FILTER="$SMTP_FROM_FILTER" \
    -e DIGIPLUS_COMPANY_EMAIL="$COMPANY_EMAIL" \
    -e DIGIPLUS_ALIAS_DOMAIN="$ALIAS_DOMAIN" \
    -e DIGIPLUS_DEFAULT_FROM_ALIAS="$DEFAULT_FROM_ALIAS" \
    -e DIGIPLUS_CATCHALL_ALIAS="$CATCHALL_ALIAS" \
    -e DIGIPLUS_BOUNCE_ALIAS="$BOUNCE_ALIAS" \
    odoo bash -lc "odoo shell -c /etc/odoo/odoo.conf -d ${DB_NAME} <<'PY'
import os

Params = env['ir.config_parameter'].sudo()
MailServer = env['ir.mail_server'].sudo()
Company = env.company.sudo()

smtp_name = os.environ['DIGIPLUS_SMTP_NAME'].strip()
smtp_from_name = os.environ['DIGIPLUS_SMTP_FROM_NAME'].strip() or 'Odoo DigiPlus'
smtp_host = os.environ['DIGIPLUS_SMTP_HOST'].strip()
smtp_port = int(os.environ['DIGIPLUS_SMTP_PORT'])
smtp_user = os.environ['DIGIPLUS_SMTP_USER'].strip()
smtp_password = os.environ['DIGIPLUS_SMTP_PASSWORD']
smtp_encryption = os.environ['DIGIPLUS_SMTP_ENCRYPTION'].strip()
smtp_from_filter = os.environ['DIGIPLUS_SMTP_FROM_FILTER'].strip()
company_email = os.environ.get('DIGIPLUS_COMPANY_EMAIL', '').strip()
alias_domain = os.environ.get('DIGIPLUS_ALIAS_DOMAIN', '').strip()
default_from_alias = os.environ.get('DIGIPLUS_DEFAULT_FROM_ALIAS', '').strip() or 'notifications'
catchall_alias = os.environ.get('DIGIPLUS_CATCHALL_ALIAS', '').strip() or 'catchall'
bounce_alias = os.environ.get('DIGIPLUS_BOUNCE_ALIAS', '').strip() or 'bounce'

server = MailServer.search([('name', '=', smtp_name)], limit=1)
vals = {
    'name': smtp_name,
    'smtp_host': smtp_host,
    'smtp_port': smtp_port,
    'smtp_user': smtp_user,
    'smtp_pass': smtp_password,
    'smtp_encryption': smtp_encryption,
    'smtp_authentication': 'login',
    'from_filter': smtp_from_filter,
    'sequence': 1,
    'active': True,
}

if server:
    server.write(vals)
else:
    server = MailServer.create(vals)

Params.set_param('mail.default.from_filter', smtp_from_filter)
Params.set_param('digiplus.mail.from_name', smtp_from_name)
if alias_domain:
    Params.set_param('mail.catchall.domain', alias_domain)
    Params.set_param('mail.default.from', default_from_alias)
    Params.set_param('mail.catchall.alias', catchall_alias)
    Params.set_param('mail.bounce.alias', bounce_alias)

if company_email:
    Company.email = company_email

test_result = server.test_smtp_connection()
env.cr.commit()

print('mail_server_id:', server.id)
print('mail_server_name:', server.name)
print('mail_server_filter:', server.from_filter)
print('mail_server_host:', server.smtp_host)
print('mail_server_port:', server.smtp_port)
print('mail_server_encryption:', server.smtp_encryption)
print('smtp_test:', test_result['params']['message'])
print('mail_default_from_filter:', Params.get_param('mail.default.from_filter'))
print('mail_from_name:', Params.get_param('digiplus.mail.from_name'))
if alias_domain:
    print('notification_address:', f'{default_from_alias}@{alias_domain}')
print('company_email:', Company.email or '')
PY"
