#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

NAME="${1:-Ojani Djeumo}"
EMAIL="${2:-ojanuethan@gmail.com}"
PHONE="${3:-687673582}"
PROJECT_NAME="${4:-Automatisation AI - Digiplus Consulting}"

if [[ ! -f .env ]]; then
    echo "Le fichier .env est introuvable dans $ROOT_DIR." >&2
    exit 1
fi

set -a
source ./.env
set +a

if [[ -z "${ODOO_DB_NAME:-}" ]]; then
    echo "ODOO_DB_NAME n'est pas defini dans .env." >&2
    exit 1
fi

if [[ -z "${DIGIPLUS_USER_PASSWORD:-}" ]]; then
    read -r -s -p "Mot de passe temporaire Odoo : " DIGIPLUS_USER_PASSWORD
    echo
fi

if [[ -z "$DIGIPLUS_USER_PASSWORD" ]]; then
    echo "Le mot de passe ne peut pas etre vide." >&2
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
    echo "Le conteneur Odoo n'est pas pret." >&2
    exit 1
fi

docker compose exec -T \
    -e DIGIPLUS_USER_NAME="$NAME" \
    -e DIGIPLUS_USER_EMAIL="$EMAIL" \
    -e DIGIPLUS_USER_PHONE="$PHONE" \
    -e DIGIPLUS_USER_PASSWORD="$DIGIPLUS_USER_PASSWORD" \
    -e DIGIPLUS_PROJECT_NAME="$PROJECT_NAME" \
    odoo bash -lc "odoo shell -c /etc/odoo/odoo.conf -d ${ODOO_DB_NAME} <<'PY'
import os

name = os.environ['DIGIPLUS_USER_NAME'].strip()
email = os.environ['DIGIPLUS_USER_EMAIL'].strip().lower()
phone = os.environ['DIGIPLUS_USER_PHONE'].strip()
password = os.environ['DIGIPLUS_USER_PASSWORD']
project_name = os.environ['DIGIPLUS_PROJECT_NAME'].strip()

Users = env['res.users'].sudo().with_context(no_reset_password=True)
Projects = env['project.project'].sudo().with_context(active_test=False)

projects = Projects.search([('name', '=ilike', project_name)], limit=2)
if not projects:
    raise SystemExit(f'Projet introuvable : {project_name}')
if len(projects) > 1:
    raise SystemExit(f'Plusieurs projets portent ce nom : {project_name}')
project = projects[0]

group_internal = env.ref('base.group_user')
group_project_user = env.ref('project.group_project_user')
group_portal = env.ref('base.group_portal', raise_if_not_found=False)
group_public = env.ref('base.group_public', raise_if_not_found=False)

groups = [(4, group_internal.id), (4, group_project_user.id)]
if group_portal:
    groups.append((3, group_portal.id))
if group_public:
    groups.append((3, group_public.id))

user = Users.search(['|', ('login', '=ilike', email), ('email', '=ilike', email)], limit=1)
values = {
    'name': name,
    'login': email,
    'email': email,
    'password': password,
    'active': True,
    'share': False,
    'groups_id': groups,
}
if user:
    user.write(values)
    action = 'mis a jour'
else:
    user = Users.create(values)
    action = 'cree'

user.partner_id.write({
    'name': name,
    'email': email,
    'phone': phone,
    'function': 'Developpeur',
})
project.message_subscribe(partner_ids=user.partner_id.ids)

if 'project.collaborator' in env:
    Collaborators = env['project.collaborator'].sudo()
    collaborator = Collaborators.search([
        ('project_id', '=', project.id),
        ('partner_id', '=', user.partner_id.id),
    ], limit=1)
    if not collaborator:
        collaborator_values = {
            'project_id': project.id,
            'partner_id': user.partner_id.id,
        }
        if 'limited_access' in Collaborators._fields:
            collaborator_values['limited_access'] = False
        Collaborators.create(collaborator_values)

env.cr.commit()
print(f'Utilisateur {action} : {user.name} <{user.login}> (id={user.id})')
print(f'Projet : {project.name} (id={project.id})')
print(f'Role : Utilisateur Projet / Developpeur')
PY"
