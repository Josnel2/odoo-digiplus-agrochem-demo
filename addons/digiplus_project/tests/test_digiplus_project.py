from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase
from lxml import etree


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

    def test_my_tasks_uses_shared_project_stages(self):
        action = self.env.ref("project.action_view_my_task")
        self.assertIn("'group_by': 'stage_id'", action.context)
        self.assertIn("'search_default_open_tasks': 1", action.context)
        self.assertIn("'digiplus_expand_project_stages': True", action.context)

    def test_my_tasks_expands_all_stages_of_visible_projects(self):
        task = self.env["project.task"].create(
            {
                "name": "Tache visible dans Mes taches",
                "project_id": self.project.id,
                "user_ids": [(6, 0, [self.env.user.id])],
            }
        )
        stages = self.env["project.task"].with_context(
            digiplus_expand_project_stages=True
        )._read_group_stage_ids(
            task.stage_id,
            [("id", "=", task.id)],
        )
        self.assertEqual(stages, self.project.type_ids.sorted("sequence"))

    def test_moving_task_to_delivered_stage_synchronizes_state(self):
        stages = self.project.type_ids.sorted("sequence")
        task = self.env["project.task"].create(
            {
                "name": "Tache a livrer",
                "project_id": self.project.id,
                "stage_id": stages[0].id,
            }
        )
        with patch.object(type(self.env["mail.mail"]), "send", return_value=True):
            task.stage_id = stages[-1]
            self.assertEqual(task.state, "1_done")

            task.stage_id = stages[1]
            self.assertEqual(task.state, "01_in_progress")

    def test_completing_task_emails_project_manager_only_on_transition(self):
        self.env.user.partner_id.email = "manager-completion@example.com"
        self.env.company.email = "notifications@example.com"
        self.project.user_id = self.env.user
        stages = self.project.type_ids.sorted("sequence")
        task = self.env["project.task"].create(
            {
                "name": "Tâche notification terminée",
                "project_id": self.project.id,
                "stage_id": stages[0].id,
            }
        )
        Mail = type(self.env["mail.mail"])
        with patch.object(Mail, "send", return_value=True) as send_mail:
            task.stage_id = stages[-1]
            self.assertEqual(send_mail.call_count, 1)
            completion_mail = self.env["mail.mail"].search(
                [("model", "=", "project.task"), ("res_id", "=", task.id)],
                order="id desc",
                limit=1,
            )
            self.assertEqual(completion_mail.email_to, "manager-completion@example.com")
            self.assertEqual(
                completion_mail.email_from,
                "Odoo DigiPlus <notifications@example.com>",
            )

            task.write({"name": "Tâche terminée renommée"})
            self.assertEqual(send_mail.call_count, 1)

            task.stage_id = stages[1]
            task.stage_id = stages[-1]
            self.assertEqual(send_mail.call_count, 2)

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
        with patch.object(type(self.env["mail.mail"]), "send", return_value=True):
            self.env["project.task"].cron_digiplus_task_deadline_alerts()
        self.assertTrue(task.digiplus_upcoming_alert_deadline)
        self.assertTrue(task.activity_ids)

    def test_deadline_alert_recipients_include_project_manager(self):
        manager = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Chef de projet alertes",
                "login": "project-manager-alerts@example.com",
                "email": "project-manager-alerts@example.com",
            }
        )
        assignee = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Responsable tâche",
                "login": "task-assignee@example.com",
                "email": "task-assignee@example.com",
            }
        )
        self.project.user_id = manager
        task = self.env["project.task"].create(
            {
                "name": "Tâche avec notification manager",
                "project_id": self.project.id,
                "user_ids": [(6, 0, assignee.ids)],
                "date_deadline": fields.Datetime.now() + timedelta(hours=24),
            }
        )

        self.assertEqual(
            set(task._get_digiplus_deadline_recipients().ids),
            {manager.id, assignee.id},
        )

    def test_weekly_report_cron_selects_manager_project_once(self):
        self.env["project.project"].search(
            [("id", "!=", self.project.id)]
        ).write({"digiplus_email_reports_enabled": False})
        self.env.user.partner_id.email = "manager@example.com"
        self.project.write(
            {
                "user_id": self.env.user.id,
                "digiplus_email_reports_enabled": True,
                "digiplus_last_report_sent_at": False,
            }
        )
        Project = type(self.env["project.project"])
        with patch.object(
            Project,
            "_send_digiplus_progress_report_email",
            autospec=True,
            return_value=True,
        ) as send_report:
            self.env["project.project"].cron_digiplus_weekly_project_reports()

        self.assertEqual(send_report.call_count, 1)
        self.assertEqual(send_report.call_args.args[0], self.project)

        self.project.digiplus_last_report_sent_at = fields.Datetime.now()
        with patch.object(
            Project,
            "_send_digiplus_progress_report_email",
            autospec=True,
            return_value=True,
        ) as send_report:
            self.env["project.project"].cron_digiplus_weekly_project_reports()

        send_report.assert_not_called()

    def test_project_dates_are_validated(self):
        with self.assertRaises(ValidationError):
            self.project.write(
                {
                    "digiplus_date_start": fields.Date.to_string(fields.Date.today()),
                    "digiplus_date_end": fields.Date.to_string(fields.Date.today() - timedelta(days=1)),
                }
            )

    def test_task_end_date_drives_overdue_status(self):
        backlog_stage = self.project.type_ids.sorted(lambda stage: (stage.sequence, stage.id))[0]
        task_start = fields.Datetime.now() - timedelta(days=2)
        task_end = fields.Datetime.now() - timedelta(hours=2)
        task = self.env["project.task"].create(
            {
                "name": "Tache en retard",
                "project_id": self.project.id,
                "stage_id": backlog_stage.id,
                "user_ids": [(6, 0, [self.env.user.id])],
                "digiplus_date_start": fields.Datetime.to_string(task_start),
                "digiplus_date_end": fields.Datetime.to_string(task_end),
                "allocated_hours": 6.0,
            }
        )
        self.assertEqual(task.date_deadline, task.digiplus_date_end)
        self.assertEqual(task.digiplus_planning_start, task.digiplus_date_start)
        self.assertEqual(task.digiplus_planning_end, task.digiplus_date_end)
        self.assertTrue(task.digiplus_is_overdue)
        self.assertEqual(task.digiplus_deadline_status, "overdue")

    def test_task_dates_are_validated(self):
        backlog_stage = self.project.type_ids.sorted(lambda stage: (stage.sequence, stage.id))[0]
        with self.assertRaises(ValidationError):
            self.env["project.task"].create(
                {
                    "name": "Tache dates invalides",
                    "project_id": self.project.id,
                    "stage_id": backlog_stage.id,
                    "digiplus_date_start": fields.Datetime.to_string(fields.Datetime.now()),
                    "digiplus_date_end": fields.Datetime.to_string(fields.Datetime.now() - timedelta(hours=1)),
                }
            )

    def test_project_form_stage_tags_do_not_request_missing_color_field(self):
        view = self.env.ref("digiplus_project.view_project_project_form_digiplus")
        root = etree.fromstring(view.arch_db.encode("utf-8"))
        stage_field = root.xpath("//field[@name='type_ids']")[0]
        self.assertEqual(stage_field.get("widget"), "many2many_tags")
        self.assertNotIn("color_field", stage_field.get("options", ""))

    def test_task_form_keeps_standard_deadline_field_anchor(self):
        view = self.env.ref("digiplus_project.view_project_task_form_digiplus")
        root = etree.fromstring(view.arch_db.encode("utf-8"))
        self.assertTrue(root.xpath("//field[@name='date_deadline']"))
        self.assertTrue(root.xpath("//field[@name='digiplus_date_start']"))

    def test_project_deliverable_updates_project_counter(self):
        deliverable = self.env["project.deliverable"].create(
            {
                "name": "Spec fonctionnelle",
                "project_id": self.project.id,
                "responsible_id": self.env.user.id,
                "status": "in_progress",
                "planned_date": fields.Date.today(),
            }
        )
        self.assertEqual(deliverable.project_id, self.project)
        self.assertEqual(self.project.digiplus_deliverable_count, 1)

    def test_dashboard_wizard_builds_metrics_and_action(self):
        backlog_stage = self.project.type_ids.sorted(lambda stage: (stage.sequence, stage.id))[0]
        self.env["project.task"].create(
            {
                "name": "Tache dashboard",
                "project_id": self.project.id,
                "stage_id": backlog_stage.id,
                "digiplus_is_blocked": True,
                "date_deadline": fields.Datetime.to_string(fields.Datetime.now() - timedelta(hours=3)),
            }
        )
        self.env["project.deliverable"].create(
            {
                "name": "Livrable dashboard",
                "project_id": self.project.id,
                "status": "blocked",
                "planned_date": fields.Date.today(),
            }
        )
        wizard = self.env["digiplus.project.dashboard.wizard"].create({"project_id": self.project.id})
        self.assertEqual(wizard.total_project_count, 1)
        self.assertGreaterEqual(wizard.blocked_task_count, 1)
        self.assertIn("Dashboard Projet", wizard.dashboard_html)
        action = wizard.action_open_projects()
        self.assertEqual(action["res_model"], "project.project")

    def test_legacy_sprint_compatibility_fields_and_action(self):
        sprint = self.env["digiplus.project.sprint"].create(
            {
                "name": "Sprint compatibilite",
                "project_id": self.project.id,
            }
        )

        self.assertEqual(self.project.digiplus_sprint_count, 1)
        self.assertFalse(self.project.digiplus_active_sprint_id)

        action = self.project.action_open_digiplus_sprints()

        self.assertEqual(action["res_model"], "digiplus.project.sprint")
        self.assertEqual(action["domain"], [("project_id", "=", self.project.id)])
        self.assertEqual(sprint.project_id, self.project)
