from odoo import fields, models

from .selections import SERVICE_SELECTION


class SaleOrder(models.Model):
    _inherit = "sale.order"

    x_service_requested = fields.Selection(SERVICE_SELECTION, string="Service demande")
