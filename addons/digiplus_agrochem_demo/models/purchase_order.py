from odoo import fields, models


PRIORITY_SELECTION = [
    ("low", "Faible"),
    ("medium", "Moyenne"),
    ("high", "Haute"),
    ("critical", "Critique"),
]


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    x_supplier_region = fields.Char(string="Region fournisseur")
    x_restock_priority = fields.Selection(PRIORITY_SELECTION, string="Priorite achat")
    x_expected_stock_impact = fields.Text(string="Impact stock attendu")
    x_agrochem_purchase_context = fields.Text(string="Contexte achat")

    def action_update_supply_comment(self):
        for order in self:
            line_names = ", ".join(order.order_line.mapped("product_id.display_name")[:3])
            order.x_expected_stock_impact = (
                "Approvisionnement en cours pour %s." % (line_names or "produits projetes")
            )
            if not order.x_agrochem_purchase_context:
                order.x_agrochem_purchase_context = (
                    "Commande preparee pour soutenir les engagements clients et la continuite des services DigiPlus."
                )
        return True

    def button_confirm(self):
        result = super().button_confirm()
        self.action_update_supply_comment()
        return result
