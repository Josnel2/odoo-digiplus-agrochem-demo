from odoo.tests.common import TransactionCase


class TestSalesFlow(TransactionCase):
    def test_create_sale_order(self):
        partner = self.env["res.partner"].create({"name": "Sale Partner", "company_type": "company"})
        product = self.env["product.product"].create(
            {
                "name": "Service DigiPlus Test",
                "type": "service",
                "list_price": 1000.0,
            }
        )
        order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "partner_invoice_id": partner.id,
                "partner_shipping_id": partner.id,
                "x_demo_proposal_type": "modular",
                "x_related_demo_axis": "CRM",
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": "Service DigiPlus Test",
                            "product_id": product.id,
                            "product_uom_qty": 1.0,
                            "price_unit": 1000.0,
                        },
                    )
                ],
            }
        )
        self.assertEqual(order.x_demo_proposal_type, "modular")
        self.assertEqual(len(order.order_line), 1)
