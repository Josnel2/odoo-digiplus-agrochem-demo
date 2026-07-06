from odoo.tests.common import TransactionCase


class TestCrmFlow(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env["res.partner"].create({"name": "Test CRM Partner", "company_type": "company"})
        self.stage_sent = self.env.ref("digiplus_crm.stage_proposal_sent")

    def test_create_opportunity(self):
        lead = self.env["crm.lead"].create(
            {
                "name": "Opportunity Test",
                "type": "opportunity",
                "partner_id": self.partner.id,
                "expected_revenue": 1500000,
                "x_interest_level": "hot",
                "x_whatsapp_followup": True,
            }
        )
        self.assertEqual(lead.x_demo_score, 90)

    def test_stage_change_generates_followup(self):
        lead = self.env["crm.lead"].create(
            {"name": "Stage Followup", "type": "opportunity", "partner_id": self.partner.id}
        )
        lead.write({"stage_id": self.stage_sent.id})
        activity = self.env["mail.activity"].search(
            [
                ("res_model", "=", "crm.lead"),
                ("res_id", "=", lead.id),
                ("summary", "=", "Relance proposition commerciale"),
            ],
            limit=1,
        )
        self.assertTrue(activity)
