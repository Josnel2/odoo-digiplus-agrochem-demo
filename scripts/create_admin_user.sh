#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ $# -lt 2 || $# -gt 3 ]]; then
    echo "Usage: $0 <email> <password> [name]" >&2
    exit 1
fi

EMAIL="$1"
PASSWORD="$2"
NAME="${3:-${EMAIL%@*}}"

set -a
source ./.env
set +a

if [[ -z "${ODOO_DB_NAME:-}" ]]; then
    echo "ODOO_DB_NAME is not defined in .env" >&2
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
    -e DIGIPLUS_ADMIN_EMAIL="$EMAIL" \
    -e DIGIPLUS_ADMIN_PASSWORD="$PASSWORD" \
    -e DIGIPLUS_ADMIN_NAME="$NAME" \
    odoo bash -lc "odoo shell -c /etc/odoo/odoo.conf -d ${ODOO_DB_NAME} <<'PY'
import os

email = os.environ['DIGIPLUS_ADMIN_EMAIL'].strip()
password = os.environ['DIGIPLUS_ADMIN_PASSWORD']
name = os.environ.get('DIGIPLUS_ADMIN_NAME', '').strip() or email.split('@', 1)[0]

Users = env['res.users'].sudo().with_context(no_reset_password=True)
group_user = env.ref('base.group_user')
group_system = env.ref('base.group_system')
group_portal = env.ref('base.group_portal', raise_if_not_found=False)
group_public = env.ref('base.group_public', raise_if_not_found=False)

user = Users.search(['|', ('login', '=', email), ('email', '=', email)], limit=1)
vals = {
    'name': name,
    'login': email,
    'email': email,
    'password': password,
    'active': True,
    'share': False,
    'groups_id': [(4, group_user.id), (4, group_system.id)],
}

if group_portal:
    vals['groups_id'].append((3, group_portal.id))
if group_public:
    vals['groups_id'].append((3, group_public.id))

if user:
    user.write(vals)
    action = 'updated'
else:
    user = Users.create(vals)
    action = 'created'

user.partner_id.write({'email': email})

print(f'{action}: id={user.id} login={user.login} name={user.name}')
print('admin_group:', group_system.display_name)
PY"
