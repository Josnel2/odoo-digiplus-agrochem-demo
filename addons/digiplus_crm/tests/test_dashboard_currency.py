from odoo.tests.common import TransactionCase


class TestDigiplusCrmDashboardCurrency(TransactionCase):
    def test_dashboard_prefers_xaf_display_currency(self):
        xaf_currency = self.env["res.currency"].with_context(active_test=False).search([("name", "=", "XAF")], limit=1)
        usd_currency = self.env["res.currency"].with_context(active_test=False).search([("name", "=", "USD")], limit=1)

        self.assertTrue(xaf_currency)
        self.assertTrue(usd_currency)

        self.env.company.currency_id = usd_currency.id
        wizard = self.env["digiplus.crm.dashboard.wizard"].create({})

        self.assertEqual(wizard.currency_id, xaf_currency)
        self.assertEqual(wizard._format_currency(38682902), "38 682 902 FCFA")
