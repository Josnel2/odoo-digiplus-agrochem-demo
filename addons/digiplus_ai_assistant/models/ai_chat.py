import json
import socket
from urllib import error, request

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


CHAT_SYSTEM_PROMPT = """Tu es l'assistant IA de gestion de projets de DigiPlus Consulting.
Transforme la demande de l'utilisateur en projet structure avec objectif, phases,
taches, risques, livrables et criteres d'acceptation. Reponds uniquement en JSON.
L'IA propose un brouillon et un humain valide avant toute creation definitive."""


class AiChatSession(models.Model):
    _name = "ai.chat.session"
    _description = "Conversation avec l'assistant IA"
    _order = "write_date desc"

    name = fields.Char(required=True, default=lambda self: _("Nouvelle conversation"))
    user_id = fields.Many2one(
        "res.users", required=True, default=lambda self: self.env.user, ondelete="cascade"
    )
    message_ids = fields.One2many("ai.chat.message", "session_id")

    @api.model
    def get_or_create_session(self):
        session = self.search([("user_id", "=", self.env.user.id)], limit=1)
        if not session:
            session = self.create({"name": _("Assistant projets")})
            self.env["ai.chat.message"].create(
                {
                    "session_id": session.id,
                    "role": "assistant",
                    "content": _(
                        "Bonjour ! Décrivez votre projet, son client et son échéance. "
                        "Je préparerai les phases, tâches, risques et livrables."
                    ),
                }
            )
        return session.id

    @api.model
    def new_session(self):
        session = self.create({"name": _("Nouvelle conversation")})
        self.env["ai.chat.message"].create(
            {
                "session_id": session.id,
                "role": "assistant",
                "content": _("Nouvelle conversation. Quel projet souhaitez-vous préparer ?"),
            }
        )
        return session.id

    def send_message(self, content):
        self.ensure_one()
        if self.user_id != self.env.user:
            raise AccessError(_("Cette conversation appartient à un autre utilisateur."))
        content = (content or "").strip()
        if not content:
            raise UserError(_("Saisissez une demande avant l'envoi."))
        if len(content) > 10000:
            raise UserError(_("La demande est trop longue (10 000 caractères maximum)."))

        Messages = self.env["ai.chat.message"]
        user_message = Messages.create(
            {"session_id": self.id, "role": "user", "content": content}
        )
        project, raw = self._generate_project(content)
        draft = self._create_draft(project, content, raw)
        task_count = len(draft.draft_task_ids)
        deliverable_count = len(draft.deliverable_ids)
        assistant_message = Messages.create(
            {
                "session_id": self.id,
                "role": "assistant",
                "content": _(
                    "J'ai préparé le brouillon « %(name)s » avec %(tasks)s tâche(s) "
                    "et %(deliverables)s livrable(s). Vous pouvez maintenant le relire."
                )
                % {
                    "name": draft.name,
                    "tasks": task_count,
                    "deliverables": deliverable_count,
                },
                "draft_id": draft.id,
            }
        )
        if self.name in (_("Nouvelle conversation"), _("Assistant projets")):
            self.name = draft.name[:100]
        return {
            "user_message": user_message.read(["role", "content", "create_date"])[0],
            "assistant_message": assistant_message.read(
                ["role", "content", "create_date", "draft_id"]
            )[0],
            "draft_id": draft.id,
        }

    def _generate_project(self, content):
        params = self.env["ir.config_parameter"].sudo()
        url = params.get_param(
            "digiplus_ai_assistant.ai_service_url", "http://ai-service:8000"
        ).rstrip("/")
        try:
            timeout = max(
                int(params.get_param("digiplus_ai_assistant.ai_service_timeout", "60")), 1
            )
        except ValueError as exc:
            raise UserError(_("Le timeout du service IA doit être un entier.")) from exc
        payload = {
            "project_name": self._project_name(content),
            "client": "",
            "description": content,
            "project_type": "Autre",
            "model": params.get_param(
                "digiplus_ai_assistant.ai_model_name", "qwen2.5:0.5b"
            ),
            "system_prompt": CHAT_SYSTEM_PROMPT,
        }
        req = request.Request(
            url + "/projects/generate",
            json.dumps(payload).encode(),
            {"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=timeout) as response:
                raw = response.read().decode()
        except (socket.timeout, TimeoutError) as exc:
            raise UserError(_("Le service IA n'a pas répondu à temps.")) from exc
        except error.HTTPError as exc:
            raise UserError(_("Le service IA a retourné l'erreur HTTP %s.") % exc.code) from exc
        except (error.URLError, OSError) as exc:
            raise UserError(_("Le service IA est indisponible : %s") % exc) from exc
        try:
            data = json.loads(raw)
            project = data["project"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise UserError(_("Le service IA a retourné une réponse invalide.")) from exc
        if not isinstance(project, dict):
            raise UserError(_("Le projet généré doit être un objet structuré."))
        return project, raw

    @api.model
    def _project_name(self, content):
        first_line = content.splitlines()[0].strip()
        return (first_line[:120] or _("Projet généré par IA"))

    def _create_draft(self, project, content, raw):
        Wizard = self.env["ai.project.generate.wizard"]
        helper = Wizard.new({"project_type": "other"})
        tasks = project.get("tasks") or project.get("kanban_cards") or []
        deliverables = project.get("deliverables") or []
        client_name = project.get("client") or ""
        partner = self.env["res.partner"].search(
            [("name", "=ilike", client_name)], limit=1
        ) if client_name else self.env["res.partner"]
        return self.env["ai.project.draft"].create(
            {
                "name": project.get("name") or self._project_name(content),
                "client_name": client_name,
                "partner_id": partner.id,
                "project_type": "other",
                "description": content,
                "objective": helper._text(project.get("objective")),
                "phases": helper._text(project.get("phases")),
                "risks": helper._text(project.get("risks")),
                "acceptance_criteria": helper._text(project.get("acceptance_criteria")),
                "ai_raw_response": raw,
                "generated_project_json": json.dumps(project, ensure_ascii=False, indent=2),
                "draft_task_ids": [
                    (0, 0, helper._task(item, index))
                    for index, item in enumerate(tasks, 1)
                    if isinstance(item, dict)
                ],
                "deliverable_ids": [
                    (0, 0, helper._deliverable(item))
                    for item in deliverables
                    if isinstance(item, (dict, str))
                ],
            }
        )


class AiChatMessage(models.Model):
    _name = "ai.chat.message"
    _description = "Message de l'assistant IA"
    _order = "id"

    session_id = fields.Many2one("ai.chat.session", required=True, ondelete="cascade")
    role = fields.Selection(
        [("user", "Utilisateur"), ("assistant", "Assistant")], required=True
    )
    content = fields.Text(required=True)
    draft_id = fields.Many2one("ai.project.draft", ondelete="set null")
