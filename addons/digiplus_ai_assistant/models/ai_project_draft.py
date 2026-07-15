from datetime import datetime, time
from markupsafe import Markup, escape
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError

PROJECT_TYPES = [("microsoft_365", "Deploiement Microsoft 365"), ("odoo", "Projet Odoo"), ("web_mobile", "Plateforme web/mobile"), ("internal_ai", "Automatisation IA interne"), ("website", "Site web client"), ("support", "Support / maintenance"), ("other", "Autre")]
TASK_STATUSES = [("backlog", "Backlog"), ("todo", "A faire"), ("in_progress", "En cours"), ("review", "En revue"), ("blocked", "Bloque"), ("done", "Termine")]


class AiProjectDraft(models.Model):
    _name = "ai.project.draft"
    _description = "Brouillon de projet IA"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(required=True, tracking=True)
    client_name = fields.Char(string="Client")
    partner_id = fields.Many2one("res.partner", string="Client identifie")
    project_type = fields.Selection(PROJECT_TYPES, required=True)
    description = fields.Text(required=True)
    objective = fields.Text()
    phases = fields.Text()
    risks = fields.Text()
    acceptance_criteria = fields.Text()
    deadline = fields.Date(tracking=True)
    ai_raw_response = fields.Text(readonly=True)
    generated_project_json = fields.Text(readonly=True)
    state = fields.Selection([("draft", "Brouillon"), ("reviewed", "Relu"), ("approved", "Approuve"), ("created", "Projet cree"), ("rejected", "Rejete")], default="draft", tracking=True)
    draft_task_ids = fields.One2many("ai.project.draft.task", "draft_id", copy=True)
    deliverable_ids = fields.One2many("ai.project.draft.deliverable", "draft_id", copy=True)
    task_count = fields.Integer(compute="_counts")
    risk_count = fields.Integer(compute="_counts")
    deliverable_count = fields.Integer(compute="_counts")
    project_id = fields.Many2one("project.project", readonly=True, copy=False)
    generated_by_id = fields.Many2one("res.users", default=lambda self: self.env.user, readonly=True)
    generated_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
    approved_by_id = fields.Many2one("res.users", readonly=True)
    approved_at = fields.Datetime(readonly=True)

    @api.depends("draft_task_ids", "deliverable_ids", "risks")
    def _counts(self):
        for rec in self:
            rec.task_count = len(rec.draft_task_ids); rec.deliverable_count = len(rec.deliverable_ids)
            rec.risk_count = len([x for x in (rec.risks or "").splitlines() if x.strip()])

    @api.onchange("client_name")
    def _find_partner(self):
        if self.client_name and not self.partner_id:
            self.partner_id = self.env["res.partner"].search([("name", "=ilike", self.client_name)], limit=1)

    def action_review(self): self.write({"state": "reviewed"})
    def action_reject(self): self.write({"state": "rejected"})
    def action_reset_draft(self): self.write({"state": "draft", "approved_by_id": False, "approved_at": False})

    def action_approve(self):
        if not self.env.user.has_group("digiplus_ai_assistant.group_ai_validator"):
            raise UserError(_("Droit de validation requis."))
        self.write({"state": "approved", "approved_by_id": self.env.user.id, "approved_at": fields.Datetime.now()})

    def action_create_odoo_project(self):
        self.ensure_one()
        if not self.env.user.has_group("digiplus_ai_assistant.group_ai_validator"): raise UserError(_("Droit de validation requis."))
        if self.project_id: raise UserError(_("Le projet a deja ete cree."))
        required = self.env["ir.config_parameter"].sudo().get_param("digiplus_ai_assistant.enable_human_validation", "True").lower() in ("true", "1")
        if required and self.state != "approved": raise UserError(_("Approuvez le brouillon avant creation."))
        if self.client_name and not self.partner_id: raise UserError(_("Client introuvable : selectionnez ou creez un contact."))
        project = self.env["project.project"].create({"name": self.name, "partner_id": self.partner_id.id, "description": Markup("<p>%s</p><h3>Objectif IA</h3><p>%s</p>") % (escape(self.description), escape(self.objective or "")), "digiplus_date_end": self.deadline})
        stages = self._stages(project)
        for task in self.draft_task_ids.sorted("sequence"):
            if not task.title: raise ValidationError(_("Une tache est sans titre."))
            deadline = datetime.combine(task.deadline, time(17)) if task.deadline else False
            self.env["project.task"].create({"name": task.title, "project_id": project.id, "partner_id": self.partner_id.id, "description": task.description_html(), "date_deadline": deadline, "digiplus_date_end": deadline, "digiplus_priority_level": task.digiplus_priority(), "digiplus_is_blocked": task.status == "blocked", "stage_id": stages[task.status].id, "allocated_hours": task.estimated_duration, "user_ids": [Command.set(task.assignee_id.ids)]})
        for item in self.deliverable_ids:
            self.env["project.deliverable"].create({"name": item.name, "project_id": project.id, "planned_date": item.deadline or self.deadline, "description": item.description})
        self.write({"project_id": project.id, "state": "created"})
        self.message_post(body=_("Projet reel cree par %s.") % self.env.user.display_name)
        return {"type": "ir.actions.act_window", "res_model": "project.project", "view_mode": "form", "res_id": project.id}

    def _stages(self, project):
        result = {}
        for sequence, (key, label) in enumerate(TASK_STATUSES, 1):
            stage = project.type_ids.filtered(lambda s: s.name.strip().lower() == label.lower())[:1]
            if not stage:
                stage = self.env["project.task.type"].sudo().create({"name": label, "sequence": sequence * 10, "fold": key == "done", "project_ids": [Command.link(project.id)]})
                project.type_ids = [Command.link(stage.id)]
            result[key] = stage
        return result


class AiProjectDraftTask(models.Model):
    _name = "ai.project.draft.task"; _description = "Tache brouillon IA"; _order = "sequence, id"
    draft_id = fields.Many2one("ai.project.draft", required=True, ondelete="cascade")
    title = fields.Char(required=True); description = fields.Text()
    priority = fields.Selection([("low", "Basse"), ("medium", "Moyenne"), ("high", "Haute"), ("critical", "Critique")], default="medium")
    status = fields.Selection(TASK_STATUSES, default="backlog"); assignee_role = fields.Char(); assignee_id = fields.Many2one("res.users")
    estimated_duration = fields.Float(); deadline = fields.Date(); acceptance_criteria = fields.Text(); phase = fields.Char(); deliverables = fields.Text(); sequence = fields.Integer(default=10)
    def digiplus_priority(self): return {"low": "low", "medium": "normal", "high": "urgent", "critical": "urgent"}[self.priority]
    def description_html(self): return Markup("<p>%s</p><h4>Criteres d'acceptation</h4><p>%s</p><h4>Livrables</h4><p>%s</p><p><b>Role :</b> %s</p>") % tuple(escape(x or "") for x in (self.description, self.acceptance_criteria, self.deliverables, self.assignee_role))


class AiProjectDraftDeliverable(models.Model):
    _name = "ai.project.draft.deliverable"; _description = "Livrable brouillon IA"
    draft_id = fields.Many2one("ai.project.draft", required=True, ondelete="cascade"); name = fields.Char(required=True); description = fields.Text(); deadline = fields.Date()
