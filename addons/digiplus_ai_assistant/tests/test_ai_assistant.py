import json
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class _FakeHttpResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


class TestAiAssistant(TransactionCase):
    def setUp(self):
        super().setUp()
        self.validator_group = self.env.ref("digiplus_ai_assistant.group_ai_validator")
        self.env.user.write({"groups_id": [Command.link(self.validator_group.id)]})
        self.partner = self.env["res.partner"].create(
            {"name": "Client IA Test", "company_type": "company"}
        )

    def _draft(self, **values):
        defaults = {
            "name": "Projet IA Test",
            "client_name": self.partner.name,
            "partner_id": self.partner.id,
            "project_type": "odoo",
            "description": "Configurer Odoo pour le client.",
            "objective": "Mettre en production le projet.",
            "deadline": "2026-12-31",
            "draft_task_ids": [
                Command.create(
                    {
                        "title": "Cadrage",
                        "status": "todo",
                        "priority": "high",
                        "estimated_duration": 8,
                        "deadline": "2026-11-30",
                    }
                )
            ],
            "deliverable_ids": [
                Command.create(
                    {
                        "name": "Dossier de cadrage",
                        "deadline": "2026-11-30",
                    }
                )
            ],
        }
        defaults.update(values)
        return self.env["ai.project.draft"].create(defaults)

    def test_generate_wizard_creates_structured_draft(self):
        response = {
            "project": {
                "name": "Déploiement Connect237",
                "client": self.partner.name,
                "objective": "Déployer Odoo",
                "phases": ["Cadrage", "Recette"],
                "risks": ["Retard de validation"],
                "acceptance_criteria": ["Recette signée"],
                "tasks": [
                    {
                        "title": "Atelier de cadrage",
                        "status": "todo",
                        "priority": "high",
                        "estimated_duration": 4,
                        "deadline": "2026-11-15",
                    }
                ],
                "deliverables": [
                    {"name": "Compte rendu", "deadline": "2026-11-15"}
                ],
            }
        }
        wizard = self.env["ai.project.generate.wizard"].create(
            {
                "project_name": "Déploiement Connect237",
                "client_name": self.partner.name,
                "description": "Préparer le déploiement Odoo.",
                "deadline": "2026-12-31",
                "project_type": "odoo",
            }
        )

        with patch(
            "odoo.addons.digiplus_ai_assistant.wizard.ai_project_generate_wizard.request.urlopen",
            return_value=_FakeHttpResponse(response),
        ):
            action = wizard.action_generate()

        draft = self.env["ai.project.draft"].browse(action["res_id"])
        self.assertEqual(draft.name, "Déploiement Connect237")
        self.assertEqual(draft.state, "draft")
        self.assertEqual(len(draft.draft_task_ids), 1)
        self.assertEqual(draft.draft_task_ids.title, "Atelier de cadrage")
        self.assertEqual(draft.draft_task_ids.priority, "high")
        self.assertEqual(len(draft.deliverable_ids), 1)

    def test_generate_wizard_rejects_past_deadline(self):
        wizard = self.env["ai.project.generate.wizard"].create(
            {
                "project_name": "Projet expiré",
                "description": "Test",
                "deadline": "2000-01-01",
                "project_type": "other",
            }
        )
        with self.assertRaises(ValidationError):
            wizard.action_generate()

    def test_approved_draft_creates_project_tasks_and_deliverables(self):
        draft = self._draft()
        draft.action_approve()
        action = draft.action_create_odoo_project()

        self.assertEqual(draft.state, "created")
        self.assertEqual(action["res_id"], draft.project_id.id)
        self.assertEqual(draft.project_id.partner_id, self.partner)
        self.assertEqual(len(draft.project_id.task_ids), 1)
        self.assertEqual(draft.project_id.task_ids.name, "Cadrage")
        deliverable = self.env["project.deliverable"].search(
            [("project_id", "=", draft.project_id.id)]
        )
        self.assertEqual(len(deliverable), 1)
        self.assertEqual(deliverable.name, "Dossier de cadrage")

    def test_unapproved_draft_cannot_create_project(self):
        draft = self._draft()
        self.env["ir.config_parameter"].sudo().set_param(
            "digiplus_ai_assistant.enable_human_validation", "True"
        )
        with self.assertRaises(UserError):
            draft.action_create_odoo_project()

    def test_draft_with_unknown_client_cannot_create_project(self):
        draft = self._draft(client_name="Client absent", partner_id=False)
        draft.action_approve()
        with self.assertRaises(UserError):
            draft.action_create_odoo_project()

    def test_chat_creates_personal_session_and_project_draft(self):
        session_id = self.env["ai.chat.session"].get_or_create_session()
        session = self.env["ai.chat.session"].browse(session_id)
        self.assertEqual(session.user_id, self.env.user)
        self.assertEqual(session.message_ids.role, "assistant")

        response = {
            "project": {
                "name": "Projet chatbot Connect237",
                "client": self.partner.name,
                "objective": "Déployer Odoo",
                "phases": ["Cadrage"],
                "tasks": [
                    {
                        "title": "Analyser le besoin",
                        "status": "todo",
                        "priority": "high",
                        "estimated_duration": 6,
                    }
                ],
                "risks": ["Retard"],
                "deliverables": ["Rapport de cadrage"],
                "acceptance_criteria": ["Validation client"],
            }
        }
        with patch(
            "odoo.addons.digiplus_ai_assistant.models.ai_chat.request.urlopen",
            return_value=_FakeHttpResponse(response),
        ):
            result = session.send_message(
                "Prépare le déploiement Odoo du client Connect237."
            )

        draft = self.env["ai.project.draft"].browse(result["draft_id"])
        self.assertEqual(draft.name, "Projet chatbot Connect237")
        self.assertEqual(draft.partner_id, self.partner)
        self.assertEqual(draft.draft_task_ids.title, "Analyser le besoin")
        self.assertEqual(draft.deliverable_ids.name, "Rapport de cadrage")
        self.assertEqual(session.message_ids.mapped("role"), ["assistant", "user", "assistant"])
        self.assertEqual(session.message_ids[-1].draft_id, draft)

    def test_chat_rejects_empty_message(self):
        session = self.env["ai.chat.session"].create({"name": "Test vide"})
        with self.assertRaises(UserError):
            session.send_message("   ")

    def test_internal_user_can_access_chat_without_ai_group(self):
        internal_group = self.env.ref("base.group_user")
        user = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Utilisateur interne IA",
                "login": "internal-ai-test@example.com",
                "groups_id": [Command.set([internal_group.id])],
            }
        )
        self.assertFalse(user.has_group("digiplus_ai_assistant.group_ai_user"))

        session_id = self.env["ai.chat.session"].with_user(user).get_or_create_session()
        session = self.env["ai.chat.session"].with_user(user).browse(session_id)
        self.assertEqual(session.user_id, user)
        self.assertEqual(len(session.message_ids), 1)
