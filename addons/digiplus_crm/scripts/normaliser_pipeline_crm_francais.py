"""
Normalise le pipeline CRM DigiPlus vers 6 etapes uniquement :
Prospect -> Qualifie -> Proposition envoyee -> Negociation -> Gagne / Perdu

Usage depuis l'hote :
docker compose exec -T odoo odoo shell -c /etc/odoo/odoo.conf -d <base> < ./addons/digiplus_crm/scripts/normaliser_pipeline_crm_francais.py
"""

Stage = env["crm.stage"]
Lead = env["crm.lead"]

PIPELINE = {
    "digiplus_crm.stage_prospect": {
        "nom": "Prospect",
        "sequence": 10,
        "pliable": False,
        "alias": ["New", "Nouveau prospect", "Prospect"],
    },
    "digiplus_crm.stage_qualified": {
        "nom": "Qualifié",
        "sequence": 20,
        "pliable": False,
        "alias": [
            "Qualified",
            "Qualifie",
            "Qualifié",
            "Besoin qualifie",
            "Besoin qualifié",
            "Atelier de cadrage",
            "Offre a preparer",
            "Offre à préparer",
        ],
    },
    "digiplus_crm.stage_proposal_sent": {
        "nom": "Proposition envoyée",
        "sequence": 30,
        "pliable": False,
        "alias": ["Proposition", "Proposition envoyee", "Proposition envoyée"],
    },
    "digiplus_crm.stage_negotiation": {
        "nom": "Négociation",
        "sequence": 40,
        "pliable": False,
        "alias": ["Negotiation", "Negociation", "Négociation", "Relance commerciale"],
    },
    "digiplus_crm.stage_won": {
        "nom": "Gagné",
        "sequence": 50,
        "pliable": True,
        "alias": ["Won", "Gagne", "Gagné", "Bon de commande recu", "Bon de commande reçu"],
    },
    "digiplus_crm.stage_lost": {
        "nom": "Perdu",
        "sequence": 60,
        "pliable": True,
        "alias": ["Lost", "Perdu"],
    },
}


def trouver_ou_creer_stage(xmlid, definition):
    stage = env.ref(xmlid, raise_if_not_found=False)
    if not stage:
        stage = Stage.search([("name", "=", definition["nom"])], limit=1)
    if not stage:
        stage = Stage.create(
            {
                "name": definition["nom"],
                "sequence": definition["sequence"],
                "fold": definition["pliable"],
            }
        )
        print(f"- stage cree : {definition['nom']}")
    else:
        stage.write(
            {
                "name": definition["nom"],
                "sequence": definition["sequence"],
                "fold": definition["pliable"],
            }
        )
        print(f"- stage mis a jour : {definition['nom']}")
    return stage


def a_coordonnees_contact(lead):
    return bool(lead.email_from or lead.phone)


def peut_etre_qualifie(lead):
    return bool(
        lead.x_service_requested
        and lead.x_need_type
        and a_coordonnees_contact(lead)
        and lead.activity_date_deadline
    )


def peut_etre_proposition(lead):
    return bool(peut_etre_qualifie(lead) and lead.expected_revenue)


def peut_etre_gagne(lead):
    return bool(
        (lead.partner_id or lead.partner_name)
        and lead.user_id
        and lead.expected_revenue
        and lead.x_service_requested
    )


def determiner_stage_final(lead, stage_cible, stages_cibles):
    prospect = stages_cibles["digiplus_crm.stage_prospect"]
    qualifie = stages_cibles["digiplus_crm.stage_qualified"]
    proposition = stages_cibles["digiplus_crm.stage_proposal_sent"]
    negociation = stages_cibles["digiplus_crm.stage_negotiation"]
    gagne = stages_cibles["digiplus_crm.stage_won"]
    perdu = stages_cibles["digiplus_crm.stage_lost"]

    if stage_cible.id == prospect.id:
        return prospect, {}

    if stage_cible.id == qualifie.id:
        return (qualifie, {}) if peut_etre_qualifie(lead) else (prospect, {})

    if stage_cible.id == proposition.id:
        if peut_etre_proposition(lead):
            return proposition, {}
        if peut_etre_qualifie(lead):
            return qualifie, {}
        return prospect, {}

    if stage_cible.id == negociation.id:
        if peut_etre_proposition(lead):
            return negociation, {}
        if peut_etre_qualifie(lead):
            return qualifie, {}
        return prospect, {}

    if stage_cible.id == gagne.id:
        if peut_etre_gagne(lead):
            return gagne, {}
        if peut_etre_proposition(lead):
            return negociation, {}
        if peut_etre_qualifie(lead):
            return qualifie, {}
        return prospect, {}

    if stage_cible.id == perdu.id:
        valeurs = {}
        if not lead.x_loss_reason:
            valeurs["x_loss_reason"] = "Perte heritee lors de la normalisation du pipeline."
        return perdu, valeurs

    return prospect, {}


stages_cibles = {}
for xmlid, definition in PIPELINE.items():
    stages_cibles[xmlid] = trouver_ou_creer_stage(xmlid, definition)

ids_cibles = {stage.id for stage in stages_cibles.values()}
statistiques = {}

for xmlid, definition in PIPELINE.items():
    stage_cible = stages_cibles[xmlid]
    alias = list(dict.fromkeys(definition["alias"] + [definition["nom"]]))
    stages_sources = Stage.search([("name", "in", alias)])
    for stage_source in stages_sources:
        if stage_source.id == stage_cible.id:
            continue
        opportunites = Lead.search([("stage_id", "=", stage_source.id)])
        if opportunites:
            for lead in opportunites:
                stage_final, valeurs = determiner_stage_final(lead, stage_cible, stages_cibles)
                valeurs = dict(valeurs)
                valeurs["stage_id"] = stage_final.id
                lead.write(valeurs)
                cle = (stage_source.name, stage_final.name)
                statistiques[cle] = statistiques.get(cle, 0) + 1
        valeurs_stage = {"fold": True}
        if "active" in Stage._fields:
            valeurs_stage["active"] = False
        stage_source.write(valeurs_stage)
        print(f"- stage archive : {stage_source.name}")

for (stage_source, stage_final), nombre in sorted(statistiques.items()):
    print(f"- {nombre} opportunite(s) deplacee(s) de '{stage_source}' vers '{stage_final}'")

stages_restants = Stage.search([("id", "not in", list(ids_cibles))])
for stage in stages_restants:
    if stage.name in [definition["nom"] for definition in PIPELINE.values()]:
        continue
    opportunites = Lead.search([("stage_id", "=", stage.id)])
    if opportunites:
        print(f"- a valider manuellement : {stage.name} ({len(opportunites)} opportunite(s))")
        continue
    valeurs_stage = {"fold": True}
    if "active" in Stage._fields:
        valeurs_stage["active"] = False
    stage.write(valeurs_stage)
    print(f"- stage supplementaire archive : {stage.name}")

env.cr.commit()
print("")
print("Pipeline CRM normalise.")
print("Etapes actives attendues : Prospect -> Qualifie -> Proposition envoyee -> Negociation -> Gagne / Perdu")
