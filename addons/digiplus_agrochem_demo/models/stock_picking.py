from odoo import fields, models


PRIORITY_SELECTION = [
    ("low", "Faible"),
    ("medium", "Moyenne"),
    ("high", "Haute"),
    ("critical", "Critique"),
]

RISK_SELECTION = [
    ("low", "Faible"),
    ("medium", "Moyen"),
    ("high", "Eleve"),
    ("critical", "Critique"),
]


class StockPicking(models.Model):
    _inherit = "stock.picking"

    x_stock_priority = fields.Selection(PRIORITY_SELECTION, string="Priorite stock")
    x_client_zone = fields.Char(string="Zone client")
    x_rupture_risk = fields.Selection(RISK_SELECTION, string="Risque de rupture")
    x_demo_comment = fields.Text(string="Commentaire operationnel")
