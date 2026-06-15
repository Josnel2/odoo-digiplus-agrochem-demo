from odoo.tests.common import TransactionCase


class TestPurchaseFlow(TransactionCase):
    def test_purchase_comment_update(self):
        supplier = self.env["res.partner"].create({"name": "Supplier DigiPlus", "supplier_rank": 1})
        product = self.env["product.product"].create(
            {
                "name": "Produit Achat Test",
                "type": "consu",
                "list_price": 1000.0,
                "standard_price": 600.0,
            }
        )
        order = self.env["purchase.order"].create(
            {
                "partner_id": supplier.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": "Produit Achat Test",
                            "product_id": product.id,
                            "product_qty": 5.0,
                            "price_unit": 600.0,
                            "date_planned": "2026-05-30 10:00:00",
                        },
                    )
                ],
            }
        )
        order.action_update_supply_comment()
        self.assertIn("Approvisionnement", order.x_expected_stock_impact)
