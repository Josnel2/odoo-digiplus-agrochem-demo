from odoo import fields, models


PROPOSAL_SELECTION = [
    ("modular", "Modulaire"),
    ("bundle", "Pack"),
    ("pilot", "Pilote"),
    ("rollout", "Deploiement"),
]

DECISION_SELECTION = [
    ("draft", "Brouillon"),
    ("in_review", "En revision"),
    ("sent", "Envoye"),
    ("approved", "Approuve"),
    ("won", "Gagne"),
]


class SaleOrder(models.Model):
    _inherit = "sale.order"

    x_demo_proposal_type = fields.Selection(PROPOSAL_SELECTION, string="Mode de proposition")
    x_related_demo_axis = fields.Char(string="Axes de la proposition")
    x_agrochem_projection = fields.Text(string="Vision de transformation")
    x_decision_status = fields.Selection(DECISION_SELECTION, string="Statut de decision", default="draft")
