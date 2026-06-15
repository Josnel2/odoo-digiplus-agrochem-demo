from odoo.tests.common import TransactionCase


class TestDigiplusCrmCompanyCurrency(TransactionCase):
    def test_company_branding_normalization_renames_demo_company(self):
        company = self.env.company
        company.name = "My Company (San Francisco)"
        company.partner_id.name = "My Company (San Francisco)"

        self.env["res.company"]._normalize_company_branding()

        self.assertEqual(company.name, "DigiPlus Consulting")
        self.assertEqual(company.partner_id.name, "DigiPlus Consulting")

    def test_currency_normalization_switches_company_and_pricelists_to_xaf(self):
        xaf_currency = self.env["res.currency"].with_context(active_test=False).search([("name", "=", "XAF")], limit=1)
        usd_currency = self.env["res.currency"].with_context(active_test=False).search([("name", "=", "USD")], limit=1)

        self.assertTrue(xaf_currency)
        self.assertTrue(usd_currency)

        pricelist = self.env["product.pricelist"].create(
            {
                "name": "USD Test Pricelist",
                "currency_id": usd_currency.id,
            }
        )
        self.env.company.currency_id = usd_currency.id

        self.env["res.company"]._normalize_company_currency_to_xaf()

        self.assertEqual(self.env.company.currency_id, xaf_currency)
        self.assertEqual(pricelist.currency_id, xaf_currency)
