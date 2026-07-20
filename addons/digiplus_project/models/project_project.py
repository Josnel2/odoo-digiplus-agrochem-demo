import base64
from datetime import timedelta
from email.utils import formataddr

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.digiplus_crm.models.selections import SERVICE_SELECTION

from .project_task import CLOSED_TASK_STATES


class ProjectProject(models.Model):
    _inherit = "project.project"

    digiplus_date_start = fields.Date(string="Date de debut", tracking=True, copy=False)
    digiplus_date_end = fields.Date(string="Date de fin", tracking=True, copy=False)
    digiplus_priority_level = fields.Selection(
        [
            ("low", "Basse"),
            ("normal", "Normale"),
            ("urgent", "Urgente"),
        ],
        string="Priorite projet",
        default="normal",
        tracking=True,
    )
    digiplus_is_template = fields.Boolean(string="Modele de projet", default=False, tracking=True, copy=False)
    origin_opportunity_id = fields.Many2one("crm.lead", string="Opportunite source", tracking=True, copy=False)
    service_requested = fields.Selection(SERVICE_SELECTION, string="Service demande", tracking=True)
    digiplus_project_status = fields.Selection(
        [
            ("planning", "En attente"),
            ("active", "Actif"),
            ("done", "Termine"),
            ("late", "En retard"),
            ("blocked", "Bloque"),
        ],
        string="Statut projet",
        compute="_compute_digiplus_operational_status",
        store=True,
    )
    digiplus_risk_level = fields.Selection(
        [
            ("normal", "Normal"),
            ("watch", "A surveiller"),
            ("high", "A risque"),
            ("critical", "Critique"),
        ],
        string="Niveau de risque",
        compute="_compute_digiplus_operational_status",
        store=True,
    )
    digiplus_global_state = fields.Selection(
        [
            ("normal", "Normal"),
            ("watch", "A surveiller"),
            ("late", "En retard"),
            ("blocked", "Bloque"),
            ("done", "Termine"),
        ],
        string="Etat global",
        compute="_compute_digiplus_operational_status",
        store=True,
    )
    digiplus_last_activity_date = fields.Datetime(
        string="Derniere activite",
        compute="_compute_digiplus_operational_status",
        store=True,
    )
    digiplus_is_late = fields.Boolean(string="Projet en retard", compute="_compute_digiplus_operational_status", store=True)
    digiplus_is_blocked = fields.Boolean(
        string="Projet bloque",
        compute="_compute_digiplus_operational_status",
        store=True,
    )
    digiplus_deliverable_ids = fields.One2many("project.deliverable", "project_id", string="Livrables")
    digiplus_deliverable_count = fields.Integer(string="Livrables", compute="_compute_digiplus_deliverable_count")
    digiplus_total_task_count = fields.Integer(string="Taches total", compute="_compute_digiplus_metrics")
    digiplus_completed_task_count = fields.Integer(string="Taches terminees", compute="_compute_digiplus_metrics")
    digiplus_overdue_task_count = fields.Integer(string="Taches en retard", compute="_compute_digiplus_metrics")
    digiplus_upcoming_task_count = fields.Integer(string="Taches sous 48h", compute="_compute_digiplus_metrics")
    digiplus_completion_rate = fields.Float(string="Completion (%)", compute="_compute_digiplus_metrics")
    digiplus_effective_hours = fields.Float(string="Heures reelles", compute="_compute_digiplus_metrics")
    digiplus_billable_hours = fields.Float(string="Heures facturables", compute="_compute_digiplus_metrics")
    digiplus_remaining_estimated_hours = fields.Float(
        string="Charge restante estimee", compute="_compute_digiplus_metrics"
    )
    digiplus_budget_variance_hours = fields.Float(string="Ecart budget (h)", compute="_compute_digiplus_metrics")
    digiplus_budget_consumption_rate = fields.Float(
        string="Consommation budget (%)", compute="_compute_digiplus_metrics"
    )
    digiplus_sprint_ids = fields.One2many(
        "digiplus.project.sprint",
        "project_id",
        string="Sprints DigiPlus",
        copy=True,
    )
    digiplus_sprint_count = fields.Integer(
        string="Nombre de sprints",
        compute="_compute_digiplus_sprint_metrics",
    )
    digiplus_active_sprint_id = fields.Many2one(
        "digiplus.project.sprint",
        string="Sprint actif",
        compute="_compute_digiplus_sprint_metrics",
    )
    digiplus_email_reports_enabled = fields.Boolean(
        string="Rapport hebdomadaire par e-mail",
        default=True,
        tracking=True,
    )
    digiplus_last_report_sent_at = fields.Datetime(
        string="Dernier rapport envoyé",
        copy=False,
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        projects = super().create(vals_list)
        projects.filtered(lambda project: not project.type_ids)._create_digiplus_default_task_stages()
        return projects

    def copy(self, default=None):
        default = dict(default or {})
        default.setdefault("origin_opportunity_id", False)
        default.setdefault("digiplus_is_template", False)
        project = super().copy(default)
        self._clone_digiplus_task_stages_to_project(project)
        return project

    def write(self, vals):
        old_partner_map = {project.id: project.partner_id.id for project in self}
        result = super().write(vals)
        if "partner_id" in vals:
            for project in self:
                old_partner_id = old_partner_map.get(project.id)
                tasks_to_update = project.tasks.filtered(
                    lambda task: not task.partner_id or task.partner_id.id == old_partner_id
                )
                tasks_to_update.write({"partner_id": project.partner_id.id or False})
        return result

    @api.constrains("digiplus_date_start", "digiplus_date_end")
    def _check_digiplus_project_dates(self):
        for project in self:
            if (
                project.digiplus_date_start
                and project.digiplus_date_end
                and project.digiplus_date_start > project.digiplus_date_end
            ):
                raise ValidationError(_("La date de debut du projet ne peut pas etre posterieure a la date de fin."))

    @api.depends("digiplus_deliverable_ids")
    def _compute_digiplus_deliverable_count(self):
        for project in self:
            project.digiplus_deliverable_count = len(project.digiplus_deliverable_ids)

    def _get_digiplus_default_stage_blueprint(self):
        return [
            {"name": _("Backlog"), "sequence": 10, "fold": False},
            {"name": _("En cours"), "sequence": 20, "fold": False},
            {"name": _("En revision"), "sequence": 30, "fold": False},
            {"name": _("Livre"), "sequence": 40, "fold": True},
        ]

    def _create_digiplus_default_task_stages(self):
        TaskStage = self.env["project.task.type"].sudo()
        for project in self:
            if project.type_ids:
                continue
            created_stages = self.env["project.task.type"]
            for stage_vals in project._get_digiplus_default_stage_blueprint():
                created_stages |= TaskStage.with_context(default_project_id=project.id).create(stage_vals)
            project.type_ids = [Command.set(created_stages.ids)]

    def _clone_digiplus_task_stages_to_project(self, new_project):
        self.ensure_one()
        TaskStage = self.env["project.task.type"].sudo()
        stage_mapping = {}
        new_stage_ids = self.env["project.task.type"]
        source_stages = self.type_ids.sorted(lambda stage: (stage.sequence, stage.id))
        for source_stage in source_stages:
            stage_vals = {
                "name": source_stage.name,
                "sequence": source_stage.sequence,
                "fold": source_stage.fold,
            }
            for field_name in ("description", "mail_template_id", "rating_template_id", "auto_validation_state"):
                if field_name not in source_stage._fields:
                    continue
                field_value = source_stage[field_name]
                if source_stage._fields[field_name].type == "many2one":
                    stage_vals[field_name] = field_value.id
                else:
                    stage_vals[field_name] = field_value
            copied_stage = TaskStage.with_context(default_project_id=new_project.id).create(stage_vals)
            stage_mapping[source_stage.id] = copied_stage.id
            new_stage_ids |= copied_stage
        if new_stage_ids:
            new_project.type_ids = [Command.set(new_stage_ids.ids)]
            tasks_to_update = new_project.tasks.filtered(lambda task: task.stage_id.id in stage_mapping)
            for task in tasks_to_update:
                task.stage_id = stage_mapping[task.stage_id.id]

    @api.depends("digiplus_sprint_ids", "digiplus_sprint_ids.state", "digiplus_sprint_ids.sequence")
    def _compute_digiplus_sprint_metrics(self):
        for project in self:
            active_sprint = project.digiplus_sprint_ids.filtered(lambda sprint: sprint.state == "active")[:1]
            project.digiplus_sprint_count = len(project.digiplus_sprint_ids)
            project.digiplus_active_sprint_id = active_sprint

    @api.depends(
        "tasks.state",
        "tasks.date_deadline",
        "tasks.user_ids",
        "tasks.allocated_hours",
        "tasks.remaining_hours",
        "tasks.digiplus_is_overdue",
        "tasks.digiplus_is_due_soon",
        "timesheet_ids.unit_amount",
        "timesheet_ids.so_line",
        "allocated_hours",
    )
    def _compute_digiplus_metrics(self):
        for project in self:
            tasks = project.tasks.filtered("display_in_project")
            open_tasks = tasks.filtered(lambda task: task.state not in CLOSED_TASK_STATES)
            leaf_open_tasks = open_tasks.filtered(lambda task: not task.child_ids)
            actual_hours = sum(project.timesheet_ids.mapped("unit_amount"))
            billable_hours = sum(project.timesheet_ids.filtered("so_line").mapped("unit_amount"))
            if project.allocated_hours:
                remaining_hours = max(project.allocated_hours - actual_hours, 0.0)
                variance_hours = project.allocated_hours - actual_hours
                consumption_rate = (actual_hours / project.allocated_hours) * 100.0
            else:
                remaining_hours = sum(
                    max(task.remaining_hours, 0.0) for task in leaf_open_tasks if "remaining_hours" in task._fields
                )
                variance_hours = -actual_hours
                consumption_rate = 0.0
            total_tasks = len(tasks)
            completed_tasks = len(tasks.filtered(lambda task: task.state in CLOSED_TASK_STATES))
            project.digiplus_total_task_count = total_tasks
            project.digiplus_completed_task_count = completed_tasks
            project.digiplus_overdue_task_count = len(open_tasks.filtered("digiplus_is_overdue"))
            project.digiplus_upcoming_task_count = len(open_tasks.filtered("digiplus_is_due_soon"))
            project.digiplus_completion_rate = round((completed_tasks / total_tasks) * 100.0, 2) if total_tasks else 0.0
            project.digiplus_effective_hours = actual_hours
            project.digiplus_billable_hours = billable_hours
            project.digiplus_remaining_estimated_hours = remaining_hours
            project.digiplus_budget_variance_hours = variance_hours
            project.digiplus_budget_consumption_rate = consumption_rate

    @api.depends(
        "active",
        "digiplus_date_start",
        "digiplus_date_end",
        "digiplus_completion_rate",
        "digiplus_overdue_task_count",
        "digiplus_upcoming_task_count",
        "digiplus_budget_consumption_rate",
        "tasks.state",
        "tasks.digiplus_is_blocked",
        "tasks.write_date",
        "digiplus_deliverable_ids.status",
        "digiplus_deliverable_ids.write_date",
        "write_date",
    )
    def _compute_digiplus_operational_status(self):
        today = fields.Date.context_today(self)
        recent_limit = fields.Datetime.now() - timedelta(days=7)
        for project in self:
            open_tasks = project.tasks.filtered(
                lambda task: task.display_in_project and task.state not in CLOSED_TASK_STATES
            )
            blocked_tasks = open_tasks.filtered("digiplus_is_blocked")
            blocked_deliverables = project.digiplus_deliverable_ids.filtered(lambda deliverable: deliverable.status == "blocked")
            latest_candidates = [value for value in [project.write_date] + open_tasks.mapped("write_date") + project.digiplus_deliverable_ids.mapped("write_date") if value]
            project.digiplus_last_activity_date = max(latest_candidates) if latest_candidates else False
            project.digiplus_is_blocked = bool(blocked_tasks or blocked_deliverables)
            late_by_date = (
                bool(project.digiplus_date_end and project.digiplus_date_end < today and project.digiplus_completion_rate < 100.0)
            )
            project.digiplus_is_late = bool(project.digiplus_overdue_task_count or late_by_date)
            if project.digiplus_completion_rate >= 100.0 and project.digiplus_total_task_count:
                project.digiplus_project_status = "done"
            elif project.digiplus_is_blocked:
                project.digiplus_project_status = "blocked"
            elif project.digiplus_is_late:
                project.digiplus_project_status = "late"
            elif project.active:
                project.digiplus_project_status = "active"
            else:
                project.digiplus_project_status = "planning"
            stale_project = bool(project.digiplus_last_activity_date and project.digiplus_last_activity_date < recent_limit)
            if project.digiplus_is_blocked or (project.digiplus_is_late and project.digiplus_overdue_task_count >= 3):
                project.digiplus_risk_level = "critical"
            elif project.digiplus_is_late or project.digiplus_budget_consumption_rate >= 95.0:
                project.digiplus_risk_level = "high"
            elif project.digiplus_upcoming_task_count or stale_project or project.digiplus_budget_consumption_rate >= 75.0:
                project.digiplus_risk_level = "watch"
            else:
                project.digiplus_risk_level = "normal"
            if project.digiplus_project_status == "done":
                project.digiplus_global_state = "done"
            elif project.digiplus_is_blocked:
                project.digiplus_global_state = "blocked"
            elif project.digiplus_is_late:
                project.digiplus_global_state = "late"
            elif project.digiplus_risk_level in ("watch", "high", "critical"):
                project.digiplus_global_state = "watch"
            else:
                project.digiplus_global_state = "normal"

    def _format_digiplus_datetime(self, value):
        self.ensure_one()
        if not value:
            return "-"
        localized_value = fields.Datetime.context_timestamp(self, value)
        return localized_value.strftime("%d/%m/%Y %H:%M")

    def _format_digiplus_hours(self, value):
        return f"{value:.2f} h"

    def _get_digiplus_service_label(self):
        self.ensure_one()
        if not self.service_requested:
            return "-"
        return dict(self._fields["service_requested"].selection).get(self.service_requested, self.service_requested)

    def _get_digiplus_progress_report_payload(self):
        self.ensure_one()
        open_tasks = self.tasks.filtered(lambda task: task.display_in_project and task.state not in CLOSED_TASK_STATES)
        task_rows = []
        for task in open_tasks.sorted(key=lambda task: task.date_deadline or fields.Datetime.now()):
            if task.state in CLOSED_TASK_STATES:
                task_progress = 100.0
            elif "progress" in task._fields:
                task_progress = round(task.progress or 0.0, 2)
            else:
                task_progress = {
                    "todo": 0.0,
                    "in_progress": 50.0,
                    "review": 80.0,
                    "blocked": 25.0,
                }.get(task.digiplus_work_state, 0.0)
            task_rows.append(
                {
                    "name": task.display_name,
                    "assignees": ", ".join(task.user_ids.mapped("name")) or "-",
                    "deadline": self._format_digiplus_datetime(task.date_deadline),
                    "priority": dict(task._fields["digiplus_priority_level"].selection).get(
                        task.digiplus_priority_level, "-"
                    ),
                    "status": dict(task._fields["digiplus_deadline_status"].selection).get(
                        task.digiplus_deadline_status, "-"
                    ),
                    "allocated_hours": self._format_digiplus_hours(task.allocated_hours or 0.0),
                    "remaining_hours": self._format_digiplus_hours(getattr(task, "remaining_hours", 0.0)),
                    "progress": task_progress,
                }
            )
        return {
            "project_name": self.display_name,
            "customer_name": self.partner_id.display_name or "-",
            "manager_name": self.user_id.display_name or "-",
            "service_label": self._get_digiplus_service_label(),
            "completion_rate": round(self.digiplus_completion_rate, 2),
            "overdue_count": self.digiplus_overdue_task_count,
            "upcoming_count": self.digiplus_upcoming_task_count,
            "total_tasks": self.digiplus_total_task_count,
            "completed_tasks": self.digiplus_completed_task_count,
            "budget_hours": self._format_digiplus_hours(self.allocated_hours or 0.0),
            "actual_hours": self._format_digiplus_hours(self.digiplus_effective_hours or 0.0),
            "billable_hours": self._format_digiplus_hours(self.digiplus_billable_hours or 0.0),
            "remaining_hours": self._format_digiplus_hours(self.digiplus_remaining_estimated_hours or 0.0),
            "variance_hours": self._format_digiplus_hours(self.digiplus_budget_variance_hours or 0.0),
            "consumption_rate": round(self.digiplus_budget_consumption_rate, 2),
            "generated_at": self._format_digiplus_datetime(fields.Datetime.now()),
            "task_rows": task_rows,
        }

    def action_view_digiplus_progress_report(self):
        self.ensure_one()
        report = self.env.ref("digiplus_project.action_report_digiplus_project_progress")
        return report.report_action(self)

    def _build_digiplus_progress_email_body(self, recipient=None):
        self.ensure_one()
        recipient = recipient or self.user_id
        return """
            <p>Bonjour %s,</p>
            <p>Veuillez trouver en pièce jointe le rapport hebdomadaire du projet
            <strong>%s</strong>.</p>
            <ul>
                <li><strong>Client :</strong> %s</li>
                <li><strong>Avancement :</strong> %.2f%%</li>
                <li><strong>Tâches terminées :</strong> %s / %s</li>
                <li><strong>Tâches en retard :</strong> %s</li>
                <li><strong>Tâches arrivant à échéance sous 48 h :</strong> %s</li>
                <li><strong>État global :</strong> %s</li>
            </ul>
            <p>Ce message a été généré automatiquement par Odoo DigiPlus.</p>
        """ % (
            recipient.name,
            self.display_name,
            self.partner_id.display_name or "-",
            self.digiplus_completion_rate,
            self.digiplus_completed_task_count,
            self.digiplus_total_task_count,
            self.digiplus_overdue_task_count,
            self.digiplus_upcoming_task_count,
            dict(self._fields["digiplus_global_state"].selection).get(
                self.digiplus_global_state, "-"
            ),
        )

    @api.model
    def _get_digiplus_email_from(self):
        params = self.env["ir.config_parameter"].sudo()
        sender_name = params.get_param("digiplus.mail.from_name", "Odoo DigiPlus")
        sender_email = self.env.company.email or params.get_param("mail.default.from_filter")
        return formataddr((sender_name, sender_email)) if sender_email else False

    @api.model
    def _get_digiplus_progress_report_recipients(self):
        project_admin_group = self.env.ref("project.group_project_manager")
        return project_admin_group.users.filtered(
            lambda user: user.active and not user.share and user.partner_id.email
        )

    def _send_digiplus_progress_report_email(self):
        self.ensure_one()
        recipients = self._get_digiplus_progress_report_recipients()
        if not recipients:
            return False
        report = self.env.ref("digiplus_project.action_report_digiplus_project_progress")
        pdf_content, _content_type = report._render_qweb_pdf(
            report.report_name,
            res_ids=self.ids,
        )
        filename = "Rapport_Projet_DigiPlus_%s.pdf" % self.display_name.replace("/", "-")
        attachment = self.env["ir.attachment"].sudo().create(
            {
                "name": filename,
                "type": "binary",
                "datas": base64.b64encode(pdf_content),
                "mimetype": "application/pdf",
                "res_model": self._name,
                "res_id": self.id,
            }
        )
        for recipient in recipients:
            mail = self.env["mail.mail"].sudo().create(
                {
                    "subject": _("Rapport hebdomadaire - %s") % self.display_name,
                    "body_html": self._build_digiplus_progress_email_body(recipient),
                    "email_from": self._get_digiplus_email_from(),
                    "email_to": recipient.partner_id.email,
                    "recipient_ids": [(6, 0, recipient.partner_id.ids)],
                    "author_id": self.env.company.partner_id.id,
                    "model": self._name,
                    "res_id": self.id,
                    "attachment_ids": [(6, 0, attachment.ids)],
                    "auto_delete": True,
                }
            )
            mail.send(raise_exception=False)
        self.digiplus_last_report_sent_at = fields.Datetime.now()
        self.message_post(
            body=_("Rapport hebdomadaire envoyé aux administrateurs Projet : %s.")
            % ", ".join(recipients.mapped("partner_id.email")),
            subtype_xmlid="mail.mt_note",
        )
        return True

    @api.model
    def cron_digiplus_weekly_project_reports(self):
        cutoff = fields.Datetime.now() - timedelta(days=6)
        projects = self.search(
            [
                ("active", "=", True),
                ("digiplus_is_template", "=", False),
                ("digiplus_email_reports_enabled", "=", True),
                "|",
                ("digiplus_last_report_sent_at", "=", False),
                ("digiplus_last_report_sent_at", "<", cutoff),
            ]
        )
        for project in projects:
            project._send_digiplus_progress_report_email()
        return True

    def action_create_project_from_template(self):
        self.ensure_one()
        new_project = self.copy(
            {
                "name": _("%s - Nouveau projet") % self.name,
                "partner_id": False,
                "origin_opportunity_id": False,
                "allow_billable": False,
                "digiplus_is_template": False,
            }
        )
        new_project.tasks.write({"partner_id": False})
        return {
            "type": "ir.actions.act_window",
            "name": _("Projet duplique"),
            "res_model": "project.project",
            "view_mode": "form",
            "res_id": new_project.id,
            "views": [(self.env.ref("project.edit_project").id, "form")],
        }

    def action_view_origin_opportunity(self):
        self.ensure_one()
        if not self.origin_opportunity_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": _("Opportunite source"),
            "res_model": "crm.lead",
            "view_mode": "form",
            "res_id": self.origin_opportunity_id.id,
        }

    def action_open_digiplus_task_stages(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("project.open_task_type_form_domain")
        action["context"] = {
            "project_id": self.id,
            "default_project_id": self.id,
        }
        return action

    def action_open_digiplus_deliverables(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("digiplus_project.action_digiplus_project_deliverables")
        action["domain"] = [("project_id", "=", self.id)]
        action["context"] = {
            "default_project_id": self.id,
            "default_responsible_id": self.user_id.id or self.env.user.id,
        }
        return action

    def action_open_digiplus_sprints(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Sprints du projet"),
            "res_model": "digiplus.project.sprint",
            "view_mode": "list,form",
            "domain": [("project_id", "=", self.id)],
            "context": {
                "default_project_id": self.id,
            },
        }
