from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .project_task import CLOSED_TASK_STATES


class DigiplusProjectSprint(models.Model):
    _name = "digiplus.project.sprint"
    _description = "Sprint projet DigiPlus"
    _order = "project_id, sequence, id"

    name = fields.Char(required=True)
    project_id = fields.Many2one("project.project", string="Projet", required=True, ondelete="cascade", index=True)
    goal = fields.Text(string="Objectif")
    date_start = fields.Date(string="Date de debut")
    date_end = fields.Date(string="Date de fin")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    state = fields.Selection(
        [
            ("planned", "Planifie"),
            ("active", "Actif"),
            ("closed", "Clos"),
        ],
        string="Statut",
        default="planned",
        required=True,
    )
    task_ids = fields.One2many("project.task", "digiplus_sprint_id", string="Taches")
    task_count = fields.Integer(string="Nombre de taches", compute="_compute_digiplus_metrics")
    open_task_count = fields.Integer(string="Taches ouvertes", compute="_compute_digiplus_metrics")
    completion_rate = fields.Float(string="Completion (%)", compute="_compute_digiplus_metrics")

    @api.depends("task_ids", "task_ids.state")
    def _compute_digiplus_metrics(self):
        for sprint in self:
            task_count = len(sprint.task_ids)
            closed_task_count = len(sprint.task_ids.filtered(lambda task: task.state in CLOSED_TASK_STATES))
            sprint.task_count = task_count
            sprint.open_task_count = task_count - closed_task_count
            sprint.completion_rate = round((closed_task_count / task_count) * 100.0, 2) if task_count else 0.0

    @api.constrains("date_start", "date_end")
    def _check_digiplus_dates(self):
        for sprint in self:
            if sprint.date_start and sprint.date_end and sprint.date_end < sprint.date_start:
                raise ValidationError(_("La date de fin du sprint doit etre posterieure a sa date de debut."))

    @api.constrains("state", "project_id")
    def _check_digiplus_single_active_sprint(self):
        for sprint in self.filtered(lambda sprint: sprint.state == "active" and sprint.project_id):
            other_active = self.search_count(
                [
                    ("project_id", "=", sprint.project_id.id),
                    ("state", "=", "active"),
                    ("id", "!=", sprint.id),
                ]
            )
            if other_active:
                raise ValidationError(_("Un seul sprint actif est autorise par projet."))

    def action_start_sprint(self):
        for sprint in self:
            other_active = self.search(
                [
                    ("project_id", "=", sprint.project_id.id),
                    ("state", "=", "active"),
                    ("id", "!=", sprint.id),
                ],
                limit=1,
            )
            if other_active:
                raise UserError(_("Le sprint %s est deja actif sur ce projet.") % other_active.display_name)
        self.write({"state": "active"})
        return True

    def action_close_sprint(self):
        self.write({"state": "closed"})
        return True

    def action_reset_to_planned(self):
        self.write({"state": "planned"})
        return True

    def action_view_tasks(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Taches du sprint"),
            "res_model": "project.task",
            "view_mode": "list,form,kanban,calendar,pivot,graph",
            "domain": [("digiplus_sprint_id", "=", self.id)],
            "context": {
                "default_project_id": self.project_id.id,
                "default_digiplus_sprint_id": self.id,
                "search_default_open_tasks": 1,
            },
        }
