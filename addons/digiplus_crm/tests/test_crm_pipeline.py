from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestDigiplusCrmPipeline(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env["res.partner"].create({"name": "Pipeline Prospect", "company_type": "company"})
        self.stage_prospect = self.env.ref("digiplus_crm.stage_prospect")
        self.stage_qualified = self.env.ref("digiplus_crm.stage_qualified")
        self.stage_proposal = self.env.ref("digiplus_crm.stage_proposal_sent")
        self.stage_lost = self.env.ref("digiplus_crm.stage_lost")
        self.activity_type = self.env.ref("digiplus_crm.activity_phonecall")

    def test_stage_qualified_requires_contact_and_priority(self):
        lead = self.env["crm.lead"].create(
            {
                "name": "Qualification CRM",
                "type": "opportunity",
                "partner_id": self.partner.id,
                "stage_id": self.stage_prospect.id,
                "user_id": self.env.user.id,
            }
        )
        self.assertTrue(lead.x_missing_next_action)

        with self.assertRaises(ValidationError):
            lead.write({"stage_id": self.stage_qualified.id})

        lead.write(
            {
                "email_from": "qualification@example.com",
                "x_service_requested": "crm",
                "x_need_type": "implementation",
                "x_priority_level": "high",
            }
        )

        lead.write({"stage_id": self.stage_qualified.id})
        self.assertEqual(lead.probability, 30)
        self.assertTrue(lead.x_missing_next_action)

    def test_stage_qualified_allows_missing_service_and_need_type(self):
        lead = self.env["crm.lead"].create(
            {
                "name": "Qualification legere",
                "type": "opportunity",
                "partner_id": self.partner.id,
                "stage_id": self.stage_prospect.id,
                "user_id": self.env.user.id,
                "email_from": "qualification-legere@example.com",
                "x_priority_level": "medium",
            }
        )
        lead.write({"stage_id": self.stage_qualified.id})
        self.assertEqual(lead.stage_id, self.stage_qualified)
        self.assertTrue(lead.x_missing_next_action)

        with self.assertRaises(ValidationError):
            lead.write({"stage_id": self.stage_proposal.id, "expected_revenue": 1000.0})

    def test_stage_proposal_allows_missing_service_and_need_type(self):
        lead = self.env["crm.lead"].create(
            {
                "name": "Proposition sans service",
                "type": "opportunity",
                "partner_id": self.partner.id,
                "stage_id": self.stage_qualified.id,
                "user_id": self.env.user.id,
                "email_from": "proposition@example.com",
                "x_priority_level": "medium",
            }
        )

        lead.write(
            {
                "stage_id": self.stage_proposal.id,
                "expected_revenue": 1000.0,
                "activity_date_deadline": "2026-05-30",
            }
        )
        self.assertEqual(lead.stage_id, self.stage_proposal)

    def test_lost_stage_allows_missing_reason(self):
        lead = self.env["crm.lead"].create(
            {
                "name": "Perte CRM",
                "type": "opportunity",
                "partner_id": self.partner.id,
                "stage_id": self.stage_prospect.id,
                "user_id": self.env.user.id,
            }
        )

        lead.write({"stage_id": self.stage_lost.id})
        self.assertEqual(lead.probability, 0)
