from odoo.tests.common import TransactionCase


class TestDigiplusCrmDashboardReport(TransactionCase):
    def test_export_dashboard_report_action(self):
        wizard = self.env["digiplus.crm.dashboard.wizard"].create({})

        payload = wizard._get_dashboard_report_payload()
        action = wizard.action_export_dashboard_report()
        if action["type"] == "ir.actions.act_window":
            # On a fresh Odoo 18 database, the first PDF export can be wrapped by
            # the document layout configurator before the actual report action.
            action = action.get("context", {}).get("report_action")

        self.assertIn("summary", payload)
        self.assertTrue(action)
        self.assertEqual(action["type"], "ir.actions.report")
        self.assertEqual(action["report_name"], "digiplus_crm.report_crm_dashboard_document")

    def test_export_dashboard_report_renders_html(self):
        wizard = self.env["digiplus.crm.dashboard.wizard"].create({})
        report = self.env.ref("digiplus_crm.action_report_crm_dashboard")

        self.assertEqual(wizard._format_percentage(0.0), "0%")

        html = report._render_qweb_html(report.report_name, wizard.ids)[0]
        if isinstance(html, bytes):
            html = html.decode()

        self.assertIn("Rapport d'analyses CRM DigiPlus", html)
        self.assertIn("Taux de conversion", html)
