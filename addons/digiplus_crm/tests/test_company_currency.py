from unittest.mock import patch

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


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

    def test_currency_normalization_keeps_company_pricelist_when_currency_change_is_blocked(self):
        xaf_currency = self.env["res.currency"].with_context(active_test=False).search([("name", "=", "XAF")], limit=1)
        usd_currency = self.env["res.currency"].with_context(active_test=False).search([("name", "=", "USD")], limit=1)

        self.assertTrue(xaf_currency)
        self.assertTrue(usd_currency)
        self.assertIn("company_id", self.env["product.pricelist"]._fields)

        company = self.env.company
        company.currency_id = usd_currency.id
        pricelist = self.env["product.pricelist"].create(
            {
                "name": "USD Company Pricelist",
                "currency_id": usd_currency.id,
                "company_id": company.id,
            }
        )

        original_method = type(self.env["res.company"])._set_company_currency_if_possible

        def fake_set_currency(model, target_company, currency):
            if target_company == company:
                raise UserError("blocked currency change")
            return original_method(model, target_company, currency)

        with patch.object(type(self.env["res.company"]), "_set_company_currency_if_possible", fake_set_currency):
            self.env["res.company"]._normalize_company_currency_to_xaf()

        self.assertEqual(company.currency_id, usd_currency)
        self.assertEqual(pricelist.currency_id, usd_currency)
