from odoo.tests.common import TransactionCase


class TestDigiplusCrmWonConversion(TransactionCase):
    def setUp(self):
        super().setUp()
        self.stage_won = self.env.ref("digiplus_crm.stage_won")

    def test_won_stage_prepares_partner_and_quote(self):
        lead = self.env["crm.lead"].create(
            {
                "name": "ERP Groupe Horizon",
                "type": "opportunity",
                "partner_name": "Horizon Group",
                "contact_name": "Fatima Ben",
                "email_from": "fatima@horizon.example",
                "phone": "+237699111222",
                "user_id": self.env.user.id,
                "stage_id": self.stage_won.id,
                "expected_revenue": 4500000,
                "x_service_requested": "erp_odoo",
                "x_priority_level": "critical",
            }
        )

        quote = self.env["sale.order"].search([("opportunity_id", "=", lead.id)], limit=1)
        self.assertTrue(lead.partner_id)
        self.assertTrue(quote)
        self.assertEqual(quote.partner_id, lead.partner_id)
        self.assertEqual(quote.x_service_requested, "erp_odoo")

    def test_won_stage_allows_missing_service(self):
        lead = self.env["crm.lead"].create(
            {
                "name": "Opportunity without service",
                "type": "opportunity",
                "partner_name": "Office Design",
                "contact_name": "Amina",
                "email_from": "amina@example.com",
                "phone": "+237600000000",
                "user_id": self.env.user.id,
                "stage_id": self.stage_won.id,
                "expected_revenue": 9000,
                "x_priority_level": "high",
            }
        )

        quote = self.env["sale.order"].search([("opportunity_id", "=", lead.id)], limit=1)
        self.assertTrue(lead.partner_id)
        self.assertTrue(quote)
        self.assertFalse(quote.x_service_requested)
