from odoo.tests.common import TransactionCase


class TestDigiplusCrmDashboardReport(TransactionCase):
    def test_export_dashboard_report_action(self):
        wizard = self.env["digiplus.crm.dashboard.wizard"].create({})

        payload = wizard._get_dashboard_report_payload()
        action = wizard.action_export_dashboard_report()

        self.assertIn("summary", payload)
        self.assertEqual(action["type"], "ir.actions.report")
