"""
Normalise le pipeline CRM DigiPlus vers 6 etapes uniquement.

Usage depuis l'hote :
docker compose exec -T odoo odoo shell -c /etc/odoo/odoo.conf -d <base> < ./addons/digiplus_crm/scripts/normaliser_pipeline_crm_francais.py
"""

env["crm.stage"]._normalize_digiplus_crm_stages()
env.cr.commit()
print("Pipeline CRM normalise.")
