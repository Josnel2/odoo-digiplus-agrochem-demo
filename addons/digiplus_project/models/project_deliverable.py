from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProjectDeliverable(models.Model):
    _name = "project.deliverable"
    _description = "Livrable projet DigiPlus"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "planned_date asc, id desc"

    name = fields.Char(string="Livrable", required=True, tracking=True)
    project_id = fields.Many2one("project.project", string="Projet", required=True, ondelete="cascade", tracking=True)
    partner_id = fields.Many2one(related="project_id.partner_id", string="Client", store=True, readonly=True)
    responsible_id = fields.Many2one("res.users", string="Responsable", tracking=True)
    status = fields.Selection(
        [
            ("draft", "En attente"),
            ("in_progress", "En cours"),
            ("review", "En revue"),
            ("blocked", "Bloque"),
            ("done", "Livre"),
            ("cancelled", "Annule"),
        ],
        string="Statut",
        default="draft",
        required=True,
        tracking=True,
    )
    planned_date = fields.Date(string="Date prevue", tracking=True)
    delivered_date = fields.Date(string="Date reelle", tracking=True)
    description = fields.Html(string="Commentaire")
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "project_deliverable_ir_attachment_rel",
        "deliverable_id",
        "attachment_id",
        string="Pieces jointes",
    )
    is_late = fields.Boolean(string="En retard", compute="_compute_schedule_flags", store=True)
    is_due_soon = fields.Boolean(string="Echeance proche", compute="_compute_schedule_flags", store=True)
    days_remaining = fields.Integer(string="Jours restants", compute="_compute_schedule_flags", store=True)
    project_status = fields.Selection(related="project_id.digiplus_project_status", string="Statut projet", store=False, readonly=True)

    @api.depends("planned_date", "delivered_date", "status")
    def _compute_schedule_flags(self):
        today = fields.Date.context_today(self)
        for deliverable in self:
            deliverable.is_late = False
            deliverable.is_due_soon = False
            deliverable.days_remaining = 0
            if deliverable.status in ("done", "cancelled"):
                continue
            if not deliverable.planned_date:
                continue
            deliverable.days_remaining = (deliverable.planned_date - today).days
            deliverable.is_late = deliverable.planned_date < today
            deliverable.is_due_soon = not deliverable.is_late and deliverable.days_remaining <= 5

    @api.constrains("planned_date", "delivered_date")
    def _check_dates(self):
        for deliverable in self:
            if deliverable.planned_date and deliverable.delivered_date and deliverable.delivered_date < deliverable.planned_date:
                raise ValidationError(_("La date reelle du livrable ne peut pas etre anterieure a la date prevue."))
