from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression


CLOSED_TASK_STATES = ("1_done", "1_canceled")


class ProjectTask(models.Model):
    _inherit = "project.task"

    digiplus_date_start = fields.Datetime(string="Date de debut", tracking=True)
    digiplus_date_end = fields.Datetime(string="Date de fin", tracking=True)
    digiplus_priority_level = fields.Selection(
        [
            ("low", "Basse"),
            ("normal", "Normale"),
            ("urgent", "Urgente"),
        ],
        string="Priorite DigiPlus",
        default="normal",
        tracking=True,
    )
    digiplus_is_due_soon = fields.Boolean(
        string="Echeance sous 48h",
        compute="_compute_digiplus_deadline_flags",
        search="_search_digiplus_is_due_soon",
    )
    digiplus_is_overdue = fields.Boolean(
        string="En retard",
        compute="_compute_digiplus_deadline_flags",
        search="_search_digiplus_is_overdue",
    )
    digiplus_deadline_status = fields.Selection(
        [
            ("on_track", "Dans les temps"),
            ("due_soon", "Echeance proche"),
            ("overdue", "En retard"),
            ("done", "Terminee"),
        ],
        string="Statut echeance",
        compute="_compute_digiplus_deadline_flags",
    )
    digiplus_planning_start = fields.Datetime(
        string="Debut planning DigiPlus",
        compute="_compute_digiplus_planning_window",
        store=True,
    )
    digiplus_planning_end = fields.Datetime(
        string="Fin planning DigiPlus",
        compute="_compute_digiplus_planning_window",
        store=True,
    )
    digiplus_upcoming_alert_deadline = fields.Datetime(copy=False)
    digiplus_overdue_alert_deadline = fields.Datetime(copy=False)

    @api.depends("digiplus_date_start", "digiplus_date_end", "date_deadline", "date_assign", "create_date", "allocated_hours")
    def _compute_digiplus_planning_window(self):
        for task in self:
            duration_hours = task.allocated_hours or 1.0
            duration_delta = timedelta(hours=duration_hours)
            fallback_start = task.date_assign or task.create_date or fields.Datetime.now()
            planning_start = task.digiplus_date_start
            planning_end = task.digiplus_date_end or task.date_deadline
            if planning_start and planning_end:
                task.digiplus_planning_start = planning_start
                task.digiplus_planning_end = planning_end
            elif planning_start:
                task.digiplus_planning_start = planning_start
                task.digiplus_planning_end = planning_start + duration_delta
            elif planning_end:
                task.digiplus_planning_end = planning_end
                task.digiplus_planning_start = planning_end - duration_delta
            else:
                task.digiplus_planning_start = fallback_start
                task.digiplus_planning_end = fallback_start + duration_delta

    @api.depends("digiplus_date_end", "date_deadline", "state")
    def _compute_digiplus_deadline_flags(self):
        now = fields.Datetime.now()
        due_soon_limit = now + timedelta(hours=48)
        for task in self:
            deadline = task.digiplus_date_end or task.date_deadline
            if task.state in CLOSED_TASK_STATES:
                task.digiplus_is_due_soon = False
                task.digiplus_is_overdue = False
                task.digiplus_deadline_status = "done"
                continue
            if not deadline:
                task.digiplus_is_due_soon = False
                task.digiplus_is_overdue = False
                task.digiplus_deadline_status = "on_track"
                continue
            task.digiplus_is_overdue = deadline < now
            task.digiplus_is_due_soon = not task.digiplus_is_overdue and deadline <= due_soon_limit
            if task.digiplus_is_overdue:
                task.digiplus_deadline_status = "overdue"
            elif task.digiplus_is_due_soon:
                task.digiplus_deadline_status = "due_soon"
            else:
                task.digiplus_deadline_status = "on_track"

    @api.model
    def _search_digiplus_is_due_soon(self, operator, value):
        now = fields.Datetime.now()
        due_soon_limit = now + timedelta(hours=48)
        due_soon_domain = [
            ("state", "not in", CLOSED_TASK_STATES),
            ("date_deadline", "!=", False),
            ("date_deadline", ">=", now),
            ("date_deadline", "<=", due_soon_limit),
        ]
        if (operator == "=" and value) or (operator == "!=" and not value):
            return due_soon_domain
        return expression.OR(
            [
                [("state", "in", CLOSED_TASK_STATES)],
                [("date_deadline", "=", False)],
                [("date_deadline", "<", now)],
                [("date_deadline", ">", due_soon_limit)],
            ]
        )

    @api.model
    def _search_digiplus_is_overdue(self, operator, value):
        now = fields.Datetime.now()
        overdue_domain = [
            ("state", "not in", CLOSED_TASK_STATES),
            ("date_deadline", "!=", False),
            ("date_deadline", "<", now),
        ]
        if (operator == "=" and value) or (operator == "!=" and not value):
            return overdue_domain
        return expression.OR(
            [
                [("state", "in", CLOSED_TASK_STATES)],
                [("date_deadline", "=", False)],
                [("date_deadline", ">=", now)],
            ]
        )

    @api.model_create_multi
    def create(self, vals_list):
        prepared_vals_list = [self._prepare_digiplus_task_vals(vals) for vals in vals_list]
        return super().create(prepared_vals_list)

    def write(self, vals):
        vals = self._prepare_digiplus_task_vals(vals)
        if "date_deadline" in vals:
            vals["digiplus_upcoming_alert_deadline"] = False
            vals["digiplus_overdue_alert_deadline"] = False
        if vals.get("state") in CLOSED_TASK_STATES:
            vals["digiplus_upcoming_alert_deadline"] = False
            vals["digiplus_overdue_alert_deadline"] = False
        return super().write(vals)

    @api.model
    def _prepare_digiplus_task_vals(self, vals):
        prepared_vals = self._prepare_digiplus_priority_vals(vals)
        if "digiplus_date_end" in prepared_vals and "date_deadline" not in prepared_vals:
            prepared_vals["date_deadline"] = prepared_vals["digiplus_date_end"]
        elif "date_deadline" in prepared_vals and "digiplus_date_end" not in prepared_vals:
            prepared_vals["digiplus_date_end"] = prepared_vals["date_deadline"]
        return prepared_vals

    @api.model
    def _prepare_digiplus_priority_vals(self, vals):
        prepared_vals = dict(vals)
        if "digiplus_priority_level" in prepared_vals and "priority" not in prepared_vals:
            prepared_vals["priority"] = "1" if prepared_vals["digiplus_priority_level"] == "urgent" else "0"
        elif "priority" in prepared_vals and "digiplus_priority_level" not in prepared_vals:
            prepared_vals["digiplus_priority_level"] = "urgent" if prepared_vals["priority"] == "1" else "normal"
        return prepared_vals

    @api.constrains("digiplus_date_start", "digiplus_date_end")
    def _check_digiplus_task_dates(self):
        for task in self:
            if task.digiplus_date_start and task.digiplus_date_end and task.digiplus_date_start > task.digiplus_date_end:
                raise ValidationError(_("La date de debut de la tache ne peut pas etre posterieure a la date de fin."))

    def _format_digiplus_deadline(self):
        self.ensure_one()
        deadline = self.digiplus_date_end or self.date_deadline
        if not deadline:
            return "-"
        localized = fields.Datetime.context_timestamp(self, deadline)
        return localized.strftime("%d/%m/%Y %H:%M")

    def _get_digiplus_assignee_names(self):
        self.ensure_one()
        return ", ".join(self.user_ids.mapped("name")) or _("Non assigne")

    def _build_digiplus_alert_subject(self, alert_kind):
        self.ensure_one()
        if alert_kind == "overdue":
            return _("Alerte DigiPlus : tache en retard")
        return _("Alerte DigiPlus : echeance dans moins de 48 heures")

    def _build_digiplus_alert_body(self, alert_kind, user):
        self.ensure_one()
        title = _("Une tache de projet est en retard.") if alert_kind == "overdue" else _(
            "Une tache de projet approche de son echeance."
        )
        return """
            <p>%s</p>
            <ul>
                <li><strong>%s</strong> %s</li>
                <li><strong>%s</strong> %s</li>
                <li><strong>%s</strong> %s</li>
                <li><strong>%s</strong> %s</li>
            </ul>
        """ % (
            title,
            _("Tache :"),
            self.display_name,
            _("Projet :"),
            self.project_id.display_name or "-",
            _("Responsable :"),
            user.name,
            _("Echeance :"),
            self._format_digiplus_deadline(),
        )

    def _schedule_digiplus_activity(self, alert_kind, user):
        self.ensure_one()
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        summary = self._build_digiplus_alert_subject(alert_kind)
        existing_activity = self.env["mail.activity"].search(
            [
                ("res_model", "=", self._name),
                ("res_id", "=", self.id),
                ("activity_type_id", "=", activity_type.id),
                ("user_id", "=", user.id),
                ("summary", "=", summary),
            ],
            limit=1,
        )
        if existing_activity:
            return
        self.activity_schedule(
            activity_type_id=activity_type.id,
            user_id=user.id,
            summary=summary,
            date_deadline=fields.Date.context_today(self),
            note=_(
                "Tache : %s\nResponsable : %s\nEcheance : %s"
            )
            % (self.display_name, user.name, self._format_digiplus_deadline()),
        )

    def _send_digiplus_deadline_email(self, alert_kind, user):
        self.ensure_one()
        if not user.partner_id.email:
            return
        mail_values = {
            "subject": self._build_digiplus_alert_subject(alert_kind),
            "body_html": self._build_digiplus_alert_body(alert_kind, user),
            "email_to": user.partner_id.email,
            "recipient_ids": [(6, 0, user.partner_id.ids)],
            "author_id": self.env.user.partner_id.id,
            "model": self._name,
            "res_id": self.id,
            "auto_delete": True,
        }
        self.env["mail.mail"].sudo().create(mail_values)

    def _trigger_digiplus_deadline_alert(self, alert_kind):
        for task in self:
            for user in task.user_ids:
                task._schedule_digiplus_activity(alert_kind, user)
                task._send_digiplus_deadline_email(alert_kind, user)
            task.message_post(
                body=_(
                    "Alerte DigiPlus envoyee (%s) pour l'echeance du %s."
                )
                % (
                    _("retard") if alert_kind == "overdue" else _("48 heures"),
                    task._format_digiplus_deadline(),
                ),
                subtype_xmlid="mail.mt_note",
            )

    @api.model
    def cron_digiplus_task_deadline_alerts(self):
        tasks = self.search(
            [
                ("display_in_project", "=", True),
                ("date_deadline", "!=", False),
                ("state", "not in", CLOSED_TASK_STATES),
                ("user_ids", "!=", False),
            ]
        )
        for task in tasks.filtered("digiplus_is_due_soon"):
            if task.digiplus_upcoming_alert_deadline == task.date_deadline:
                continue
            task._trigger_digiplus_deadline_alert("upcoming")
            task.digiplus_upcoming_alert_deadline = task.date_deadline
        for task in tasks.filtered("digiplus_is_overdue"):
            if task.digiplus_overdue_alert_deadline == task.date_deadline:
                continue
            task._trigger_digiplus_deadline_alert("overdue")
            task.digiplus_overdue_alert_deadline = task.date_deadline
        return True
