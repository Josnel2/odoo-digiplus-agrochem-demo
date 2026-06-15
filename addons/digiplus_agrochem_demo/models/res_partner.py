from odoo import fields, models


SECTOR_SELECTION = [
    ("industry", "Industrie"),
    ("distribution", "Distribution"),
    ("services", "Services"),
    ("education", "Education"),
    ("health", "Sante"),
    ("hospitality", "Hotellerie"),
    ("technology", "Technologies"),
]

CLIENT_TYPE_SELECTION = [
    ("prospect", "Prospect"),
    ("client", "Client"),
    ("partner", "Partenaire"),
    ("supplier", "Fournisseur"),
]

CHANNEL_SELECTION = [
    ("email", "Email"),
    ("phone", "Telephone"),
    ("whatsapp", "WhatsApp"),
    ("onsite", "Visite"),
    ("linkedin", "LinkedIn"),
]

POTENTIAL_SELECTION = [
    ("medium", "Moyen"),
    ("high", "Fort"),
    ("strategic", "Strategique"),
]

PRIORITY_SELECTION = [
    ("low", "Faible"),
    ("medium", "Moyenne"),
    ("high", "Haute"),
    ("critical", "Critique"),
]


class ResPartner(models.Model):
    _inherit = "res.partner"

    x_company_sector = fields.Selection(SECTOR_SELECTION, string="Secteur")
    x_geographic_zone = fields.Char(string="Zone geographique")
    x_client_type = fields.Selection(CLIENT_TYPE_SELECTION, string="Type de client")
    x_preferred_channel = fields.Selection(CHANNEL_SELECTION, string="Canal prefere")
    x_account_potential = fields.Selection(POTENTIAL_SELECTION, string="Potentiel compte")
    x_priority_level = fields.Selection(PRIORITY_SELECTION, string="Niveau de priorite")
    x_last_business_interaction = fields.Date(string="Derniere interaction")
    x_business_context = fields.Text(string="Contexte business")
    x_agrochem_equivalent_segment = fields.Char(string="Segment de compte")
