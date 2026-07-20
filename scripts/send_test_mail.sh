#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ $# -lt 1 || $# -gt 3 ]]; then
    echo "Usage: $0 <to_email> [subject] [db_name]" >&2
    exit 1
fi

TO_EMAIL="$1"
SUBJECT="${2:-Test email DigiPlus Odoo}"

set -a
source ./.env
set +a

DB_NAME="${3:-${ODOO_DB_NAME:-}}"
ALIAS_DOMAIN="${DIGIPLUS_ALIAS_DOMAIN:-}"
DEFAULT_FROM_ALIAS="${DIGIPLUS_DEFAULT_FROM_ALIAS:-notifications}"
FORCED_FROM="${DIGIPLUS_TEST_EMAIL_FROM:-${DIGIPLUS_COMPANY_EMAIL:-}}"

if [[ -z "$DB_NAME" ]]; then
    echo "ODOO_DB_NAME is not defined and no database was passed as argument." >&2
    exit 1
fi

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
    -e DIGIPLUS_TEST_TO="$TO_EMAIL" \
    -e DIGIPLUS_TEST_SUBJECT="$SUBJECT" \
    -e DIGIPLUS_ALIAS_DOMAIN="$ALIAS_DOMAIN" \
    -e DIGIPLUS_DEFAULT_FROM_ALIAS="$DEFAULT_FROM_ALIAS" \
    -e DIGIPLUS_TEST_EMAIL_FROM="$FORCED_FROM" \
    odoo bash -lc "odoo shell -c /etc/odoo/odoo.conf -d ${DB_NAME} <<'PY'
import os
from email.utils import formataddr

to_email = os.environ['DIGIPLUS_TEST_TO'].strip()
subject = os.environ['DIGIPLUS_TEST_SUBJECT'].strip()
forced_from = os.environ.get('DIGIPLUS_TEST_EMAIL_FROM', '').strip()
alias_domain = os.environ.get('DIGIPLUS_ALIAS_DOMAIN', '').strip()
default_from_alias = os.environ.get('DIGIPLUS_DEFAULT_FROM_ALIAS', '').strip() or 'notifications'

company_email = env.company.email or ''
email_from = forced_from or company_email
if not email_from and alias_domain:
    email_from = f'{default_from_alias}@{alias_domain}'
if not email_from:
    raise ValueError('Unable to determine email_from. Set DIGIPLUS_COMPANY_EMAIL or DIGIPLUS_ALIAS_DOMAIN.')
if '<' not in email_from:
    sender_name = env['ir.config_parameter'].sudo().get_param('digiplus.mail.from_name', 'Odoo DigiPlus')
    email_from = formataddr((sender_name, email_from))

mail = env['mail.mail'].sudo().create({
    'subject': subject,
    'body_html': '<p>Test email envoye depuis Odoo DigiPlus.</p>',
    'email_from': email_from,
    'email_to': to_email,
    'auto_delete': True,
})
mail.send()

print('sent_mail_id:', mail.id)
print('email_from:', email_from)
print('email_to:', to_email)
print('subject:', subject)
PY"
