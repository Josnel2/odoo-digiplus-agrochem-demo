from datetime import timedelta
from email.utils import formataddr

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression


CLOSED_TASK_STATES = ("1_done", "1_canceled")
MOSCOW_SELECTION = [
    ("must", "Must"),
    ("should", "Should"),
    ("could", "Could"),
    ("wont", "Wont"),
]


class ProjectTask(models.Model):
    _inherit = "project.task"

    digiplus_date_start = fields.Datetime(string="Date de debut", tracking=True)
    digiplus_date_end = fields.Datetime(string="Date de fin", tracking=True)
    digiplus_is_blocked = fields.Boolean(string="Bloquee", tracking=True)
    digiplus_blocking_reason = fields.Text(string="Raison du blocage", tracking=True)
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
    digiplus_moscow_priority = fields.Selection(
        MOSCOW_SELECTION,
        string="Priorite MoSCoW",
        default="should",
        tracking=True,
    )
    digiplus_sprint_id = fields.Many2one(
        "digiplus.project.sprint",
        string="Sprint",
        copy=False,
        index=True,
        tracking=True,
    )
    digiplus_dependency_ids = fields.Many2many(
        "project.task",
        "digiplus_task_dependency_rel",
        "task_id",
        "dependency_id",
        string="Dependances",
        copy=False,
    )
    digiplus_blocking_task_ids = fields.Many2many(
        "project.task",
        "digiplus_task_dependency_rel",
        "dependency_id",
        "task_id",
        string="Bloque d'autres taches",
        readonly=True,
    )
    digiplus_open_dependency_count = fields.Integer(
        string="Dependances ouvertes",
        compute="_compute_digiplus_dependency_state",
        store=True,
    )
    digiplus_is_blocked_by_dependencies = fields.Boolean(
        string="Bloquee par dependances",
        compute="_compute_digiplus_dependency_state",
        store=True,
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
    digiplus_work_state = fields.Selection(
        [
            ("todo", "A faire"),
            ("in_progress", "En cours"),
            ("review", "En revue"),
            ("blocked", "Bloquee"),
            ("done", "Terminee"),
        ],
        string="Etat de travail",
        compute="_compute_digiplus_work_state",
        store=True,
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

    @api.depends("digiplus_dependency_ids", "digiplus_dependency_ids.state")
    def _compute_digiplus_dependency_state(self):
        for task in self:
            open_dependencies = task.digiplus_dependency_ids.filtered(
                lambda dependency: dependency.state not in CLOSED_TASK_STATES
            )
            task.digiplus_open_dependency_count = len(open_dependencies)
            task.digiplus_is_blocked_by_dependencies = bool(open_dependencies)

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

    @api.depends("state", "stage_id", "digiplus_is_blocked", "digiplus_is_blocked_by_dependencies")
    def _compute_digiplus_work_state(self):
        for task in self:
            if task.state in CLOSED_TASK_STATES:
                task.digiplus_work_state = "done"
                continue
            if task.digiplus_is_blocked or task.digiplus_is_blocked_by_dependencies:
                task.digiplus_work_state = "blocked"
                continue
            task.digiplus_work_state = task._get_digiplus_stage_work_state()

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
        previously_open = self.filtered(lambda task: task.state not in CLOSED_TASK_STATES)
        if "date_deadline" in vals:
            vals["digiplus_upcoming_alert_deadline"] = False
            vals["digiplus_overdue_alert_deadline"] = False
        if vals.get("state") in CLOSED_TASK_STATES:
            vals["digiplus_upcoming_alert_deadline"] = False
            vals["digiplus_overdue_alert_deadline"] = False
        result = super().write(vals)
        newly_completed = previously_open.filtered(lambda task: task.state == "1_done")
        newly_completed._notify_digiplus_task_completed()
        return result

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        if not self.env.context.get("digiplus_expand_project_stages"):
            return super()._read_group_stage_ids(stages, domain)
        visible_tasks = self.search(domain)
        project_ids = visible_tasks.project_id.ids
        if not project_ids:
            return stages
        return self.env["project.task.type"].search(
            [
                ("project_ids", "in", project_ids),
                ("user_id", "=", False),
            ],
            order="sequence, id",
        )

    @api.model
    def _prepare_digiplus_task_vals(self, vals):
        prepared_vals = self._prepare_digiplus_priority_vals(vals)
        if prepared_vals.get("stage_id") and "state" not in prepared_vals:
            stage = self.env["project.task.type"].browse(prepared_vals["stage_id"])
            normalized_name = (stage.name or "").strip().lower()
            is_delivered = stage.fold or any(
                token in normalized_name
                for token in ("livre", "livré", "termine", "terminé", "done", "closed")
            )
            prepared_vals["state"] = "1_done" if is_delivered else "01_in_progress"
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

    @api.constrains("project_id", "digiplus_sprint_id", "digiplus_dependency_ids")
    def _check_digiplus_task_relations(self):
        for task in self:
            if task.digiplus_sprint_id and task.digiplus_sprint_id.project_id != task.project_id:
                raise ValidationError(_("Le sprint choisi doit appartenir au meme projet que la tache."))
            if task in task.digiplus_dependency_ids:
                raise ValidationError(_("Une tache ne peut pas dependre d'elle-meme."))
            cross_project_dependencies = task.digiplus_dependency_ids.filtered(
                lambda dependency: dependency.project_id != task.project_id
            )
            if cross_project_dependencies:
                raise ValidationError(_("Les dependances doivent appartenir au meme projet que la tache."))
            if task._has_digiplus_dependency_cycle():
                raise ValidationError(_("Une boucle de dependances a ete detectee entre les taches du projet."))

    def _has_digiplus_dependency_cycle(self):
        self.ensure_one()

        def visit(task, path):
            if task.id in path:
                return True
            next_path = set(path)
            next_path.add(task.id)
            return any(visit(dependency, next_path) for dependency in task.digiplus_dependency_ids)

        return any(visit(dependency, {self.id}) for dependency in self.digiplus_dependency_ids)

    def _format_digiplus_deadline(self):
        self.ensure_one()
        deadline = self.digiplus_date_end or self.date_deadline
        if not deadline:
            return "-"
        localized = fields.Datetime.context_timestamp(self, deadline)
        return localized.strftime("%d/%m/%Y %H:%M")

    def _get_digiplus_stage_work_state(self):
        self.ensure_one()
        normalized_stage = (self.stage_id.name or "").strip().lower()
        if any(token in normalized_stage for token in ("review", "revision", "revue", "validation", "qa")):
            return "review"
        if any(
            token in normalized_stage
            for token in ("cours", "progress", "doing", "develop", "build", "production", "execution")
        ):
            return "in_progress"
        return "todo"

    def _get_digiplus_assignee_names(self):
        self.ensure_one()
        return ", ".join(self.user_ids.mapped("name")) or _("Non assigne")

    @api.model
    def _get_digiplus_email_from(self):
        params = self.env["ir.config_parameter"].sudo()
        sender_name = params.get_param("digiplus.mail.from_name", "Odoo DigiPlus")
        sender_email = self.env.company.email or params.get_param("mail.default.from_filter")
        return formataddr((sender_name, sender_email)) if sender_email else False

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
            note=_("Tache : %s\nResponsable : %s\nEcheance : %s")
            % (self.display_name, user.name, self._format_digiplus_deadline()),
        )

    def _send_digiplus_deadline_email(self, alert_kind, user):
        self.ensure_one()
        if not user.partner_id.email:
            return
        mail_values = {
            "subject": self._build_digiplus_alert_subject(alert_kind),
            "body_html": self._build_digiplus_alert_body(alert_kind, user),
            "email_from": self._get_digiplus_email_from(),
            "email_to": user.partner_id.email,
            "recipient_ids": [(6, 0, user.partner_id.ids)],
            "author_id": self.env.user.partner_id.id,
            "model": self._name,
            "res_id": self.id,
            "auto_delete": True,
        }
        mail = self.env["mail.mail"].sudo().create(mail_values)
        mail.send(raise_exception=False)

    def _get_digiplus_deadline_recipients(self):
        self.ensure_one()
        recipients = self.user_ids
        if self.project_id.user_id:
            recipients |= self.project_id.user_id
        return recipients.filtered(lambda user: user.active and user.partner_id.email)

    def _notify_digiplus_task_completed(self):
        for task in self:
            manager = task.project_id.user_id
            if not manager or not manager.active or not manager.partner_id.email:
                continue
            body_html = """
                <p>Bonjour %s,</p>
                <p>La tâche <strong>%s</strong> vient d'être terminée.</p>
                <ul>
                    <li><strong>Projet :</strong> %s</li>
                    <li><strong>Responsable(s) :</strong> %s</li>
                    <li><strong>Échéance :</strong> %s</li>
                </ul>
                <p>Vous pouvez consulter le projet dans Odoo DigiPlus.</p>
            """ % (
                manager.name,
                task.display_name,
                task.project_id.display_name,
                task._get_digiplus_assignee_names(),
                task._format_digiplus_deadline(),
            )
            mail = self.env["mail.mail"].sudo().create(
                {
                    "subject": _("Tâche terminée - %s") % task.display_name,
                    "body_html": body_html,
                    "email_from": task._get_digiplus_email_from(),
                    "email_to": manager.partner_id.email,
                    "recipient_ids": [(6, 0, manager.partner_id.ids)],
                    "author_id": self.env.company.partner_id.id,
                    "model": task._name,
                    "res_id": task.id,
                    "auto_delete": True,
                }
            )
            mail.send(raise_exception=False)
            task.message_post(
                body=_("Notification de fin de tâche envoyée à %s.")
                % manager.partner_id.email,
                subtype_xmlid="mail.mt_note",
            )

    def _trigger_digiplus_deadline_alert(self, alert_kind):
        for task in self:
            for user in task._get_digiplus_deadline_recipients():
                task._schedule_digiplus_activity(alert_kind, user)
                task._send_digiplus_deadline_email(alert_kind, user)
            task.message_post(
                body=_("Alerte DigiPlus envoyee (%s) pour l'echeance du %s.")
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
