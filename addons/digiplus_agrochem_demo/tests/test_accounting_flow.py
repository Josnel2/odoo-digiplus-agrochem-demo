from odoo.tests.common import TransactionCase


class TestAccountingFlow(TransactionCase):
    def test_export_status_selection_includes_not_exported(self):
        selection = dict(self.env["account.move"]._fields["x_sage_saari_export_status"].selection)
        self.assertIn("not_exported", selection)

    def test_mark_ready_for_export_does_not_change_invoice_state(self):
        invoice = self.env.ref("digiplus_agrochem_demo.invoice_orbit_finance")
        original_state = invoice.state
        invoice.action_mark_ready_for_export()
        self.assertEqual(invoice.x_sage_saari_export_status, "ready")
        self.assertEqual(invoice.state, original_state)

    def test_legacy_sage_action_alias_marks_invoice_ready_for_export(self):
        invoice = self.env.ref("digiplus_agrochem_demo.invoice_orbit_finance")
        invoice.x_sage_saari_export_status = "not_exported"

        invoice.action_mark_ready_for_sage()

        self.assertEqual(invoice.x_sage_saari_export_status, "ready")

    def test_demo_invoice_uses_sale_journal_and_consistent_dates(self):
        invoice = self.env.ref("digiplus_agrochem_demo.invoice_greenpath_support")

        self.assertEqual(invoice.move_type, "out_invoice")
        self.assertEqual(invoice.journal_id.type, "sale")
        self.assertGreaterEqual(invoice.invoice_date_due, invoice.invoice_date)
        self.assertGreater(invoice.amount_total, 0.0)

    def test_demo_invoice_links_back_to_sale_order_and_opportunity(self):
        invoice = self.env.ref("digiplus_agrochem_demo.invoice_greenpath_support")

        self.assertEqual(
            invoice.x_related_sale_order_id,
            self.env.ref("digiplus_agrochem_demo.sale_order_greenpath_support"),
        )
        self.assertEqual(
            invoice.x_related_opportunity_id,
            self.env.ref("digiplus_agrochem_demo.lead_greenpath_support"),
        )
        self.assertEqual(invoice.x_workflow_origin, "crm")

    def test_mark_ready_for_export_enriches_comment_with_sales_context(self):
        invoice = self.env.ref("digiplus_agrochem_demo.invoice_orbit_finance")
        invoice.write(
            {
                "x_sage_saari_export_status": "not_exported",
                "x_integration_comment": False,
            }
        )

        invoice.action_mark_ready_for_export()

        self.assertEqual(invoice.x_sage_saari_export_status, "ready")
        self.assertIn(invoice.x_related_sale_order_id.name, invoice.x_integration_comment)
        self.assertIn(invoice.x_related_opportunity_id.display_name, invoice.x_integration_comment)
