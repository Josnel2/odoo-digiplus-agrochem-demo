SERVICE_SELECTION = [
    ("erp_odoo", "ERP / Odoo"),
    ("crm", "CRM"),
    ("web", "Développement web"),
    ("mobile", "Développement mobile"),
    ("automation", "Automatisation"),
    ("bi", "Business Intelligence"),
    ("training", "Formation"),
    ("support", "Maintenance / Support"),
    ("digital_marketing", "Marketing digital"),
    ("it_consulting", "Conseil IT"),
]

BUSINESS_SECTOR_SELECTION = [
    ("it_services", "Services IT"),
    ("retail", "Distribution"),
    ("industry", "Industrie"),
    ("finance", "Finance"),
    ("education", "Éducation"),
    ("health", "Santé"),
    ("hospitality", "Hôtellerie"),
    ("logistics", "Logistique"),
    ("public_sector", "Secteur public"),
    ("other", "Autre"),
]

PRIORITY_SELECTION = [
    ("low", "Faible"),
    ("medium", "Moyenne"),
    ("high", "Haute"),
    ("critical", "Critique"),
]

CONTACT_LANGUAGE_SELECTION = [
    ("fr_FR", "Français"),
    ("en_US", "Anglais"),
]

NEED_TYPE_SELECTION = [
    ("implementation", "Implémentation"),
    ("upgrade", "Évolution"),
    ("audit", "Audit"),
    ("training", "Formation"),
    ("support", "Support"),
    ("migration", "Migration"),
    ("other", "Autre"),
]

STAGE_PROBABILITY_BY_XMLID = {
    "digiplus_crm.stage_prospect": 10,
    "digiplus_crm.stage_qualified": 30,
    "digiplus_crm.stage_proposal_sent": 60,
    "digiplus_crm.stage_negotiation": 80,
    "digiplus_crm.stage_won": 100,
    "digiplus_crm.stage_lost": 0,
}
