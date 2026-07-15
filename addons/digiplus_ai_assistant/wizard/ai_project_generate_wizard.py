import json, socket
from urllib import error, request
from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.addons.digiplus_ai_assistant.models.ai_project_draft import PROJECT_TYPES

SYSTEM_PROMPT = "Tu es l'assistant IA operationnel de DigiPlus Consulting integre a Odoo. Structure projets, taches, Kanban, livrables, risques et criteres d'acceptation. Produis uniquement un JSON exploitable. Sois realiste pour une PME technologique camerounaise. L'IA propose ; l'humain valide les decisions sensibles."

class AiProjectGenerateWizard(models.TransientModel):
    _name = "ai.project.generate.wizard"; _description = "Generer un projet avec IA"
    project_name = fields.Char(required=True); client_name = fields.Char(); description = fields.Text(required=True); deadline = fields.Date(); project_type = fields.Selection(PROJECT_TYPES, required=True, default="other")

    def action_generate(self):
        self.ensure_one()
        if self.deadline and self.deadline < fields.Date.context_today(self): raise ValidationError(_("Echeance invalide."))
        p = self.env["ir.config_parameter"].sudo(); url = p.get_param("digiplus_ai_assistant.ai_service_url", "http://ai-service:8000").rstrip("/")
        try: timeout = max(int(p.get_param("digiplus_ai_assistant.ai_service_timeout", "60")), 1)
        except ValueError as exc: raise UserError(_("Le timeout doit etre entier.")) from exc
        payload = {"project_name": self.project_name, "client": self.client_name or "", "description": self.description, "deadline": fields.Date.to_string(self.deadline) if self.deadline else None, "project_type": dict(PROJECT_TYPES)[self.project_type], "model": p.get_param("digiplus_ai_assistant.ai_model_name", "qwen2.5:0.5b"), "system_prompt": SYSTEM_PROMPT}
        req = request.Request(url + "/projects/generate", json.dumps(payload).encode(), {"Content-Type": "application/json"}, method="POST")
        try:
            with request.urlopen(req, timeout=timeout) as response: raw = response.read().decode()
        except (socket.timeout, TimeoutError) as exc: raise UserError(_("Delai du service IA depasse.")) from exc
        except error.HTTPError as exc: raise UserError(_("Erreur HTTP IA %s.") % exc.code) from exc
        except (error.URLError, OSError) as exc: raise UserError(_("Service IA indisponible : %s") % exc) from exc
        try: data = json.loads(raw); project = data["project"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc: raise UserError(_("Reponse IA JSON invalide.")) from exc
        tasks = project.get("tasks") or project.get("kanban_cards") or []
        vals = {"name": project.get("name") or self.project_name, "client_name": project.get("client") or self.client_name, "project_type": self.project_type, "description": self.description, "objective": self._text(project.get("objective")), "phases": self._text(project.get("phases")), "risks": self._text(project.get("risks")), "acceptance_criteria": self._text(project.get("acceptance_criteria")), "deadline": self.deadline, "ai_raw_response": raw, "generated_project_json": json.dumps(project, ensure_ascii=False, indent=2), "draft_task_ids": [(0, 0, self._task(x, i)) for i, x in enumerate(tasks, 1) if isinstance(x, dict)], "deliverable_ids": [(0, 0, self._deliverable(x)) for x in project.get("deliverables", [])]}
        draft = self.env["ai.project.draft"].create(vals); draft.message_post(body=_("Generation demandee par %s.") % self.env.user.display_name)
        return {"type": "ir.actions.act_window", "res_model": "ai.project.draft", "view_mode": "form", "res_id": draft.id}

    def _text(self, v): return "\n".join("- " + (x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)) for x in v) if isinstance(v, list) else (json.dumps(v, ensure_ascii=False, indent=2) if isinstance(v, dict) else v or "")
    def _date(self, v):
        try: return fields.Date.to_date(str(v)[:10]) if v else False
        except ValueError: return False
    def _task(self, x, i):
        priorities = {"low", "medium", "high", "critical"}; statuses = {"backlog", "todo", "in_progress", "review", "blocked", "done"}; status = str(x.get("status", "backlog")).lower(); priority = str(x.get("priority", "medium")).lower()
        return {"title": x.get("title") or x.get("name") or _("Tache %s") % i, "description": self._text(x.get("description")), "priority": priority if priority in priorities else "medium", "status": status if status in statuses else "backlog", "assignee_role": x.get("assignee_role") or x.get("role"), "estimated_duration": float(x.get("estimated_duration") or 0), "deadline": self._date(x.get("deadline")), "acceptance_criteria": self._text(x.get("acceptance_criteria")), "phase": x.get("phase"), "deliverables": self._text(x.get("deliverables")), "sequence": i * 10}
    def _deliverable(self, x): return {"name": x if isinstance(x, str) else x.get("name") or x.get("title") or _("Livrable"), "description": "" if isinstance(x, str) else self._text(x.get("description")), "deadline": False if isinstance(x, str) else self._date(x.get("deadline"))}
