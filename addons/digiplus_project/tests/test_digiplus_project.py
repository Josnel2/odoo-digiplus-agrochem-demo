from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestDigiplusProject(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env["res.partner"].create({"name": "Client Projet DigiPlus", "company_type": "company"})
        self.project = self.env["project.project"].create(
            {
                "name": "Projet Pilotage DigiPlus",
                "partner_id": self.partner.id,
                "allocated_hours": 40.0,
                "allow_timesheets": True,
                "allow_billable": True,
            }
        )

    def test_default_task_stages_created_on_project_creation(self):
        self.assertEqual(len(self.project.type_ids), 4)
        self.assertEqual(
            self.project.type_ids.sorted(lambda stage: (stage.sequence, stage.id)).mapped("name"),
            ["Backlog", "En cours", "En revision", "Livre"],
        )

    def test_template_duplication_creates_project_specific_stages(self):
        self.project.digiplus_is_template = True
        copied_project = self.project.copy({"name": "Projet Copie DigiPlus"})
        self.assertEqual(len(copied_project.type_ids), 4)
        self.assertFalse(set(copied_project.type_ids.ids) & set(self.project.type_ids.ids))

    def test_crm_lead_creates_linked_project(self):
        stage_won = self.env.ref("digiplus_crm.stage_won")
        lead = self.env["crm.lead"].create(
            {
                "name": "Projet depuis CRM",
                "type": "opportunity",
                "partner_name": self.partner.name,
                "partner_id": self.partner.id,
                "email_from": "contact@digiplus.example",
                "phone": "+237690000001",
                "user_id": self.env.user.id,
                "expected_revenue": 50000.0,
                "stage_id": stage_won.id,
                "x_priority_level": "high",
            }
        )
        action = lead.action_create_digiplus_project()
        created_project = self.env["project.project"].browse(action["res_id"])
        self.assertEqual(created_project.origin_opportunity_id, lead)
        self.assertEqual(created_project.partner_id, lead.partner_id)

    def test_due_soon_alert_creates_activity(self):
        backlog_stage = self.project.type_ids.sorted(lambda stage: (stage.sequence, stage.id))[0]
        due_soon_deadline = fields.Datetime.to_string(fields.Datetime.now() + timedelta(hours=24))
        task = self.env["project.task"].create(
            {
                "name": "Alerte echeance proche",
                "project_id": self.project.id,
                "stage_id": backlog_stage.id,
                "user_ids": [(6, 0, [self.env.user.id])],
                "date_deadline": due_soon_deadline,
                "allocated_hours": 4.0,
                "digiplus_priority_level": "urgent",
            }
        )
        self.env["project.task"].cron_digiplus_task_deadline_alerts()
        self.assertTrue(task.digiplus_upcoming_alert_deadline)
        self.assertTrue(task.activity_ids)
