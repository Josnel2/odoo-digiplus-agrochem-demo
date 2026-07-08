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

    def test_demo_sale_order_reflects_exported_invoice_status(self):
        order = self.env.ref("digiplus_agrochem_demo.sale_order_greenpath_support")

        self.assertEqual(order.x_workflow_invoice_count, 1)
        self.assertEqual(order.x_last_invoice_id, self.env.ref("digiplus_agrochem_demo.invoice_greenpath_support"))
        self.assertEqual(order.x_accounting_export_status, "exported")
        self.assertEqual(order.x_accounting_flow_status, "exported")

    def test_demo_sale_order_reflects_ready_invoice_status(self):
        order = self.env.ref("digiplus_agrochem_demo.sale_order_orbit_finance")

        self.assertEqual(order.x_workflow_invoice_count, 1)
        self.assertEqual(order.x_last_invoice_id, self.env.ref("digiplus_agrochem_demo.invoice_orbit_finance"))
        self.assertEqual(order.x_accounting_export_status, "ready")
        self.assertEqual(order.x_accounting_flow_status, "ready_for_export")

    def test_open_workflow_invoices_returns_invoice_form_action(self):
        order = self.env.ref("digiplus_agrochem_demo.sale_order_greenpath_support")

        action = order.action_open_workflow_invoices()

        self.assertEqual(action["res_model"], "account.move")
        self.assertEqual(action["view_mode"], "form")
        self.assertEqual(action["res_id"], self.env.ref("digiplus_agrochem_demo.invoice_greenpath_support").id)
