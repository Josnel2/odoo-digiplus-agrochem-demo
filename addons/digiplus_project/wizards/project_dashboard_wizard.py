from collections import defaultdict
from datetime import date, timedelta

from markupsafe import escape

from odoo import _, api, fields, models

from odoo.addons.digiplus_project.models.project_task import CLOSED_TASK_STATES


class ProjectDashboardWizard(models.TransientModel):
    _name = "digiplus.project.dashboard.wizard"
    _description = "Dashboard Projet DigiPlus"
    _rec_name = "name"
    _transient_max_hours = 72.0

    name = fields.Char(string="Nom", default=lambda self: _("Dashboard Projet DigiPlus"), readonly=True)
    period_filter = fields.Selection(
        [
            ("30", "30 derniers jours"),
            ("7", "7 prochains jours"),
            ("90", "90 jours"),
            ("custom", "Periode personnalisee"),
            ("all", "Toutes periodes"),
        ],
        string="Periode",
        default="all",
        required=True,
    )
    date_from = fields.Date(string="Date de debut")
    date_to = fields.Date(string="Date de fin")
    project_id = fields.Many2one("project.project", string="Projet")
    partner_id = fields.Many2one("res.partner", string="Client")
    manager_id = fields.Many2one("res.users", string="Responsable")
    status_filter = fields.Selection(
        [
            ("planning", "En attente"),
            ("active", "Actif"),
            ("done", "Termine"),
            ("late", "En retard"),
            ("blocked", "Bloque"),
        ],
        string="Statut projet",
    )
    priority_filter = fields.Selection(
        [
            ("low", "Basse"),
            ("normal", "Normale"),
            ("urgent", "Urgente"),
        ],
        string="Priorite",
    )
    overdue_only = fields.Boolean(string="Retards uniquement")
    blocked_only = fields.Boolean(string="Blocages uniquement")
    updated_at_display = fields.Char(string="Mise a jour", compute="_compute_dashboard")
    total_project_count = fields.Integer(string="Total projets", compute="_compute_dashboard")
    active_project_count = fields.Integer(string="Projets actifs", compute="_compute_dashboard")
    completed_project_count = fields.Integer(string="Projets termines", compute="_compute_dashboard")
    late_project_count = fields.Integer(string="Projets en retard", compute="_compute_dashboard")
    risk_project_count = fields.Integer(string="Projets a risque", compute="_compute_dashboard")
    global_progress_rate = fields.Float(string="Avancement moyen", compute="_compute_dashboard")
    todo_task_count = fields.Integer(string="Taches a faire", compute="_compute_dashboard")
    in_progress_task_count = fields.Integer(string="Taches en cours", compute="_compute_dashboard")
    review_task_count = fields.Integer(string="Taches en revue", compute="_compute_dashboard")
    blocked_task_count = fields.Integer(string="Taches bloquees", compute="_compute_dashboard")
    done_task_count = fields.Integer(string="Taches terminees", compute="_compute_dashboard")
    unassigned_task_count = fields.Integer(string="Sans responsable", compute="_compute_dashboard")
    due_soon_task_count = fields.Integer(string="Echeances proches", compute="_compute_dashboard")
    budget_planned_hours = fields.Float(string="Budget prevu", compute="_compute_dashboard")
    budget_consumed_hours = fields.Float(string="Budget consomme", compute="_compute_dashboard")
    budget_remaining_hours = fields.Float(string="Budget restant", compute="_compute_dashboard")
    dashboard_html = fields.Html(string="Dashboard", compute="_compute_dashboard", sanitize=False)

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        start_date, end_date = self._get_range_for_period("all")
        values.setdefault("date_from", start_date)
        values.setdefault("date_to", end_date)
        return values

    @api.onchange("period_filter")
    def _onchange_period_filter(self):
        if self.period_filter == "custom":
            return
        self.date_from, self.date_to = self._get_range_for_period(self.period_filter)

    @api.depends(
        "period_filter",
        "date_from",
        "date_to",
        "project_id",
        "partner_id",
        "manager_id",
        "status_filter",
        "priority_filter",
        "overdue_only",
        "blocked_only",
    )
    def _compute_dashboard(self):
        now = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        for wizard in self:
            projects = wizard._get_filtered_projects()
            tasks = wizard._get_filtered_tasks(projects)
            deliverables = wizard._get_filtered_deliverables(projects)

            todo_tasks = tasks.filtered(lambda task: task.digiplus_work_state == "todo")
            in_progress_tasks = tasks.filtered(lambda task: task.digiplus_work_state == "in_progress")
            review_tasks = tasks.filtered(lambda task: task.digiplus_work_state == "review")
            blocked_tasks = tasks.filtered(lambda task: task.digiplus_work_state == "blocked")
            done_tasks = tasks.filtered(lambda task: task.digiplus_work_state == "done")
            unassigned_tasks = tasks.filtered(lambda task: not task.user_ids and task.state not in CLOSED_TASK_STATES)

            wizard.total_project_count = len(projects)
            wizard.active_project_count = len(projects.filtered(lambda project: project.digiplus_project_status == "active"))
            wizard.completed_project_count = len(projects.filtered(lambda project: project.digiplus_project_status == "done"))
            wizard.late_project_count = len(projects.filtered("digiplus_is_late"))
            wizard.risk_project_count = len(
                projects.filtered(lambda project: project.digiplus_risk_level in ("high", "critical"))
            )
            wizard.global_progress_rate = (
                round(sum(projects.mapped("digiplus_completion_rate")) / len(projects), 2) if projects else 0.0
            )
            wizard.todo_task_count = len(todo_tasks)
            wizard.in_progress_task_count = len(in_progress_tasks)
            wizard.review_task_count = len(review_tasks)
            wizard.blocked_task_count = len(blocked_tasks)
            wizard.done_task_count = len(done_tasks)
            wizard.unassigned_task_count = len(unassigned_tasks)
            wizard.due_soon_task_count = len(tasks.filtered("digiplus_is_due_soon"))
            wizard.budget_planned_hours = sum(projects.mapped("allocated_hours"))
            wizard.budget_consumed_hours = sum(projects.mapped("digiplus_effective_hours"))
            wizard.budget_remaining_hours = sum(projects.mapped("digiplus_remaining_estimated_hours"))
            wizard.updated_at_display = now.strftime("%d/%m/%Y %H:%M") if now else ""
            wizard.dashboard_html = wizard._render_dashboard(projects, tasks, deliverables)

    @api.model
    def _get_range_for_period(self, period_filter):
        today = fields.Date.context_today(self)
        if period_filter == "7":
            return today, today + timedelta(days=7)
        if period_filter == "90":
            return today - timedelta(days=89), today
        if period_filter == "all":
            return False, False
        end_date = today
        start_date = end_date - timedelta(days=29)
        return start_date, end_date

    def _get_filtered_projects(self):
        self.ensure_one()
        domain = [("digiplus_is_template", "=", False)]
        if self.project_id:
            domain.append(("id", "=", self.project_id.id))
        if self.partner_id:
            domain.append(("partner_id", "=", self.partner_id.id))
        if self.manager_id:
            domain.append(("user_id", "=", self.manager_id.id))
        if self.status_filter:
            domain.append(("digiplus_project_status", "=", self.status_filter))
        if self.priority_filter:
            domain.append(("digiplus_priority_level", "=", self.priority_filter))
        if self.overdue_only:
            domain.append(("digiplus_is_late", "=", True))
        if self.blocked_only:
            domain.append(("digiplus_is_blocked", "=", True))
        projects = self.env["project.project"].with_context(active_test=False).search(domain)
        if self.period_filter != "all" and self.date_from and self.date_to:
            projects = projects.filtered(self._project_matches_period)
        return projects

    def _get_filtered_tasks(self, projects):
        self.ensure_one()
        if not projects:
            return self.env["project.task"]
        tasks = self.env["project.task"].search(
            [
                ("project_id", "in", projects.ids),
                ("display_in_project", "=", True),
            ]
        )
        if self.blocked_only:
            tasks = tasks.filtered("digiplus_is_blocked")
        if self.overdue_only:
            tasks = tasks.filtered("digiplus_is_overdue")
        if self.period_filter != "all" and self.date_from and self.date_to:
            tasks = tasks.filtered(self._task_matches_period)
        return tasks

    def _get_filtered_deliverables(self, projects):
        self.ensure_one()
        if not projects:
            return self.env["project.deliverable"]
        deliverables = self.env["project.deliverable"].search([("project_id", "in", projects.ids)])
        if self.blocked_only:
            deliverables = deliverables.filtered(lambda deliverable: deliverable.status == "blocked")
        if self.overdue_only:
            deliverables = deliverables.filtered("is_late")
        if self.period_filter != "all" and self.date_from and self.date_to:
            deliverables = deliverables.filtered(self._deliverable_matches_period)
        return deliverables

    def _project_matches_period(self, project):
        self.ensure_one()
        date_from = self.date_from
        date_to = self.date_to
        if not (date_from and date_to):
            return True
        candidates = [project.digiplus_date_start, project.digiplus_date_end]
        candidates += project.tasks.mapped("digiplus_date_end")
        candidates += project.digiplus_deliverable_ids.mapped("planned_date")
        candidates = [candidate for candidate in candidates if candidate]
        if not candidates:
            project_create_date = project.create_date.date() if project.create_date else False
            return bool(project_create_date and date_from <= project_create_date <= date_to)
        return any(date_from <= fields.Date.to_date(candidate) <= date_to for candidate in candidates)

    def _task_matches_period(self, task):
        self.ensure_one()
        date_from = self.date_from
        date_to = self.date_to
        if not (date_from and date_to):
            return True
        deadline = task.digiplus_date_end or task.date_deadline
        if deadline:
            deadline_date = fields.Date.to_date(deadline)
            return date_from <= deadline_date <= date_to
        if task.digiplus_date_start:
            start_date = fields.Date.to_date(task.digiplus_date_start)
            return date_from <= start_date <= date_to
        created_date = task.create_date.date() if task.create_date else False
        return bool(created_date and date_from <= created_date <= date_to)

    def _deliverable_matches_period(self, deliverable):
        self.ensure_one()
        if not (self.date_from and self.date_to):
            return True
        for value in (deliverable.planned_date, deliverable.delivered_date):
            if value and self.date_from <= value <= self.date_to:
                return True
        created_date = deliverable.create_date.date() if deliverable.create_date else False
        return bool(created_date and self.date_from <= created_date <= self.date_to)

    def _render_dashboard(self, projects, tasks, deliverables):
        self.ensure_one()
        project_rows = self._build_project_rows(projects)
        alert_rows = self._build_alert_rows(projects, tasks, deliverables)
        workload_rows = self._build_workload_rows(tasks)
        deliverable_rows = self._build_deliverable_rows(deliverables)
        deadline_rows = self._build_deadline_rows(tasks, deliverables)
        return "".join(
            [
                "<div style=\"display:flex;flex-direction:column;gap:18px;\">",
                self._render_kpi_cards(),
                self._render_project_panel(project_rows),
                self._render_task_panels(tasks),
                self._render_alert_panel(alert_rows),
                self._render_workload_panel(workload_rows),
                self._render_deadline_panel(deadline_rows),
                self._render_deliverable_panel(deliverable_rows),
                self._render_budget_panel(projects),
                "</div>",
            ]
        )

    def _build_project_rows(self, projects):
        today = fields.Date.context_today(self)
        rows = []
        for project in projects.sorted(
            key=lambda project: (
                0 if project.digiplus_global_state == "blocked" else 1,
                0 if project.digiplus_is_late else 1,
                project.digiplus_date_end or today,
                project.name or "",
            )
        ):
            deadline = project.digiplus_date_end or self._get_nearest_task_deadline(project.tasks)
            days_remaining = self._get_days_remaining(deadline)
            rows.append(
                {
                    "name": project.display_name,
                    "client": project.partner_id.display_name or "-",
                    "manager": project.user_id.display_name or "-",
                    "status": self._get_selection_label("digiplus_project_status", project.digiplus_project_status),
                    "priority": self._get_selection_label("digiplus_priority_level", project.digiplus_priority_level),
                    "progress": round(project.digiplus_completion_rate or 0.0, 2),
                    "start": self._format_date(project.digiplus_date_start),
                    "deadline": self._format_date(deadline),
                    "tasks": "%s / %s" % (project.digiplus_completed_task_count, project.digiplus_total_task_count),
                    "days_remaining": self._format_days_remaining(days_remaining),
                    "global_state": self._get_selection_label("digiplus_global_state", project.digiplus_global_state),
                    "global_tone": self._get_tone_from_state(project.digiplus_global_state),
                }
            )
        return rows

    def _build_alert_rows(self, projects, tasks, deliverables):
        today = fields.Date.context_today(self)
        recent_limit = fields.Datetime.now() - timedelta(days=7)
        rows = []
        for task in tasks.filtered("digiplus_is_overdue")[:5]:
            rows.append(
                {
                    "category": _("Tache en retard"),
                    "name": task.display_name,
                    "project": task.project_id.display_name or "-",
                    "detail": task._format_digiplus_deadline(),
                    "tone": "danger",
                }
            )
        for task in tasks.filtered(lambda task: not task.user_ids and task.state not in CLOSED_TASK_STATES)[:5]:
            rows.append(
                {
                    "category": _("Sans responsable"),
                    "name": task.display_name,
                    "project": task.project_id.display_name or "-",
                    "detail": _("A assigner"),
                    "tone": "warning",
                }
            )
        for project in projects.filtered(
            lambda project: project.digiplus_date_end
            and 0 <= (project.digiplus_date_end - today).days <= 5
            and project.digiplus_project_status not in ("done", "late", "blocked")
        )[:4]:
            rows.append(
                {
                    "category": _("Projet proche de la deadline"),
                    "name": project.display_name,
                    "project": project.display_name,
                    "detail": self._format_date(project.digiplus_date_end),
                    "tone": "warning",
                }
            )
        for project in projects.filtered(
            lambda project: project.digiplus_last_activity_date and project.digiplus_last_activity_date < recent_limit
        )[:4]:
            rows.append(
                {
                    "category": _("Sans avancement recent"),
                    "name": project.display_name,
                    "project": project.display_name,
                    "detail": self._format_datetime(project.digiplus_last_activity_date),
                    "tone": "neutral",
                }
            )
        for project in projects.filtered("digiplus_is_blocked")[:4]:
            rows.append(
                {
                    "category": _("Projet bloque"),
                    "name": project.display_name,
                    "project": project.display_name,
                    "detail": _("Action manager requise"),
                    "tone": "danger",
                }
            )
        for deliverable in deliverables.filtered(lambda deliverable: deliverable.is_late or deliverable.is_due_soon)[:5]:
            rows.append(
                {
                    "category": _("Livrable critique"),
                    "name": deliverable.name,
                    "project": deliverable.project_id.display_name or "-",
                    "detail": self._format_date(deliverable.planned_date),
                    "tone": "danger" if deliverable.is_late else "warning",
                }
            )
        return rows[:12]

    def _build_workload_rows(self, tasks):
        open_tasks = tasks.filtered(lambda task: task.state not in CLOSED_TASK_STATES)
        grouped = defaultdict(
            lambda: {"assigned": 0, "in_progress": 0, "overdue": 0, "blocked": 0, "allocated_hours": 0.0}
        )
        for task in open_tasks:
            for user in task.user_ids:
                values = grouped[user]
                values["assigned"] += 1
                if task.digiplus_work_state in ("in_progress", "review"):
                    values["in_progress"] += 1
                if task.digiplus_is_overdue:
                    values["overdue"] += 1
                if task.digiplus_is_blocked:
                    values["blocked"] += 1
                values["allocated_hours"] += task.allocated_hours or 0.0
        rows = []
        for user, values in sorted(grouped.items(), key=lambda item: (-item[1]["assigned"], item[0].display_name)):
            load_level = self._get_load_level(values["assigned"], values["allocated_hours"], values["overdue"], values["blocked"])
            rows.append(
                {
                    "member": user.display_name,
                    "assigned": values["assigned"],
                    "in_progress": values["in_progress"],
                    "overdue": values["overdue"],
                    "blocked": values["blocked"],
                    "load_level": load_level[0],
                    "load_tone": load_level[1],
                    "allocated_hours": values["allocated_hours"],
                }
            )
        return rows

    def _build_deadline_rows(self, tasks, deliverables):
        rows = []
        for task in tasks.filtered(lambda task: task.state not in CLOSED_TASK_STATES and (task.digiplus_date_end or task.date_deadline)).sorted(
            key=lambda task: task.digiplus_date_end or task.date_deadline
        )[:6]:
            rows.append(
                {
                    "label": task.display_name,
                    "kind": _("Tache"),
                    "project": task.project_id.display_name or "-",
                    "owner": ", ".join(task.user_ids.mapped("name")) or _("Non assigne"),
                    "date": self._format_datetime(task.digiplus_date_end or task.date_deadline),
                    "tone": "danger" if task.digiplus_is_overdue else "warning" if task.digiplus_is_due_soon else "neutral",
                }
            )
        for deliverable in deliverables.filtered(lambda deliverable: deliverable.status not in ("done", "cancelled") and deliverable.planned_date).sorted(
            key=lambda deliverable: deliverable.planned_date
        )[:6]:
            rows.append(
                {
                    "label": deliverable.name,
                    "kind": _("Livrable"),
                    "project": deliverable.project_id.display_name or "-",
                    "owner": deliverable.responsible_id.display_name or _("Non assigne"),
                    "date": self._format_date(deliverable.planned_date),
                    "tone": "danger" if deliverable.is_late else "warning" if deliverable.is_due_soon else "neutral",
                }
            )
        rows.sort(key=lambda row: row["date"])
        return rows[:10]

    def _build_deliverable_rows(self, deliverables):
        rows = []
        for deliverable in deliverables.sorted(
            key=lambda deliverable: (
                0 if deliverable.is_late else 1,
                0 if deliverable.status == "blocked" else 1,
                deliverable.planned_date or date.max,
            )
        )[:10]:
            rows.append(
                {
                    "name": deliverable.name,
                    "project": deliverable.project_id.display_name or "-",
                    "owner": deliverable.responsible_id.display_name or "-",
                    "status": self._get_selection_label("status", deliverable.status, record=deliverable),
                    "planned_date": self._format_date(deliverable.planned_date),
                    "delivered_date": self._format_date(deliverable.delivered_date),
                    "comment": self._truncate_text(deliverable.description or ""),
                    "tone": "danger" if deliverable.is_late else "warning" if deliverable.is_due_soon else "success" if deliverable.status == "done" else "neutral",
                }
            )
        return rows

    def _dashboard_palette(self):
        return {
            "panel_bg": "#FFFFFF",
            "surface": "#F6F7F9",
            "border": "#DEE2E6",
            "soft_border": "#E9ECEF",
            "text": "#212529",
            "muted": "#6C757D",
            "subtle": "#98A2B3",
            "shadow": "0 10px 24px rgba(113, 75, 103, 0.08)",
            "primary": "#714B67",
            "primary_bg": "#F3EDF1",
            "success": "#198754",
            "success_bg": "#EAF6EE",
            "warning": "#B57B00",
            "warning_bg": "#FFF4D8",
            "danger": "#C0392B",
            "danger_bg": "#FCEBE9",
            "info": "#0F7C90",
            "info_bg": "#E6F4F6",
            "neutral": "#6C757D",
            "neutral_bg": "#F1F3F5",
        }

    def _get_tone_color(self, tone, variant="text"):
        palette = self._dashboard_palette()
        if variant == "background":
            return palette.get("%s_bg" % tone, palette["neutral_bg"])
        return palette.get(tone, palette["neutral"])

    def _panel_style(self):
        palette = self._dashboard_palette()
        return (
            "border:1px solid {border};border-radius:16px;background:{panel_bg};"
            "padding:18px;box-shadow:{shadow};"
        ).format(**palette)

    def _metric_card_style(self, tone):
        palette = self._dashboard_palette()
        return (
            "background:{background};border-radius:14px;padding:14px 16px;"
            "border:1px solid {border};box-shadow:inset 0 3px 0 {accent};"
        ).format(
            background=self._get_tone_color(tone, "background"),
            border=palette["soft_border"],
            accent=self._get_tone_color(tone),
        )

    def _render_kpi_cards(self):
        palette = self._dashboard_palette()
        cards = [
            (_("Total projets"), self.total_project_count, "primary"),
            (_("Projets actifs"), self.active_project_count, "success"),
            (_("Projets termines"), self.completed_project_count, "info"),
            (_("Projets en retard"), self.late_project_count, "danger"),
            (_("Projets a risque"), self.risk_project_count, "warning"),
            (_("Avancement moyen"), "%s%%" % round(self.global_progress_rate, 2), "neutral"),
        ]
        html = [
            "<div style=\"display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:14px;\">",
        ]
        for label, value, tone in cards:
            html.extend(
                [
                    "<div style=\"%s\">" % self._metric_card_style(tone),
                    "<div style=\"font-size:12px;font-weight:700;color:%s;text-transform:uppercase;letter-spacing:0.04em;\">%s</div>"
                    % (palette["muted"], escape(label)),
                    "<div style=\"margin-top:10px;font-size:28px;font-weight:800;color:%s;\">%s</div>"
                    % (self._get_tone_color(tone), escape(str(value))),
                    "</div>",
                ]
            )
        html.append("</div>")
        return "".join(html)

    def _render_project_panel(self, rows):
        if not rows:
            return self._render_empty_panel(_("Tableau des projets"), _("Aucun projet a afficher pour les filtres choisis."))
        body_rows = []
        for row in rows:
            body_rows.extend(
                [
                    "<tr>",
                    "<td>%s</td>" % escape(row["name"]),
                    "<td>%s</td>" % escape(row["client"]),
                    "<td>%s</td>" % escape(row["manager"]),
                    "<td>%s</td>" % self._render_badge(row["status"], self._get_tone_from_state(row["status"].lower())),
                    "<td>%s</td>" % escape(row["priority"]),
                    "<td>%s%%</td>" % escape(str(row["progress"])),
                    "<td>%s</td>" % escape(row["start"]),
                    "<td>%s</td>" % escape(row["deadline"]),
                    "<td>%s</td>" % escape(row["tasks"]),
                    "<td>%s</td>" % escape(row["days_remaining"]),
                    "<td>%s</td>" % self._render_badge(row["global_state"], row["global_tone"]),
                    "</tr>",
                ]
            )
        return self._render_table_panel(
            title=_("Tableau des projets"),
            subtitle=_("Vision synthetique des projets clients et internes"),
            headers=[
                _("Projet"),
                _("Client"),
                _("Responsable"),
                _("Statut"),
                _("Priorite"),
                _("Avancement"),
                _("Date debut"),
                _("Deadline"),
                _("Taches"),
                _("Jours restants"),
                _("Etat global"),
            ],
            rows_html="".join(body_rows),
        )

    def _render_task_panels(self, tasks):
        palette = self._dashboard_palette()
        cards = [
            (_("A faire"), len(tasks.filtered(lambda task: task.digiplus_work_state == "todo")), "neutral"),
            (_("En cours"), len(tasks.filtered(lambda task: task.digiplus_work_state == "in_progress")), "primary"),
            (_("En revue"), len(tasks.filtered(lambda task: task.digiplus_work_state == "review")), "warning"),
            (_("Bloquees"), len(tasks.filtered(lambda task: task.digiplus_work_state == "blocked")), "danger"),
            (_("Terminees"), len(tasks.filtered(lambda task: task.digiplus_work_state == "done")), "info"),
            (_("En retard"), len(tasks.filtered("digiplus_is_overdue")), "danger"),
        ]
        parts = [
            "<div style=\"%s\">" % self._panel_style(),
            "<div style=\"font-size:18px;font-weight:800;color:%s;margin-bottom:12px;\">%s</div>"
            % (palette["text"], escape(_("Suivi des taches"))),
            "<div style=\"display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:12px;\">",
        ]
        for label, value, tone in cards:
            parts.extend(
                [
                    "<div style=\"%s\">" % self._metric_card_style(tone),
                    "<div style=\"font-size:12px;color:%s;font-weight:700;text-transform:uppercase;\">%s</div>"
                    % (palette["muted"], escape(label)),
                    "<div style=\"margin-top:8px;font-size:24px;font-weight:800;color:%s;\">%s</div>"
                    % (self._get_tone_color(tone), escape(str(value))),
                    "</div>",
                ]
            )
        parts.extend(["</div>", "</div>"])
        return "".join(parts)

    def _render_alert_panel(self, rows):
        if not rows:
            return self._render_empty_panel(_("Alertes projet"), _("Aucune alerte critique sur le perimetre selectionne."))
        body_rows = []
        for row in rows:
            body_rows.extend(
                [
                    "<tr>",
                    "<td>%s</td>" % self._render_badge(row["category"], row["tone"]),
                    "<td>%s</td>" % escape(row["name"]),
                    "<td>%s</td>" % escape(row["project"]),
                    "<td>%s</td>" % escape(row["detail"]),
                    "</tr>",
                ]
            )
        return self._render_table_panel(
            title=_("Alertes projet"),
            subtitle=_("Retards, taches sans responsable, livrables critiques et projets a surveiller"),
            headers=[_("Categorie"), _("Element"), _("Projet"), _("Detail")],
            rows_html="".join(body_rows),
        )

    def _render_workload_panel(self, rows):
        if not rows:
            return self._render_empty_panel(_("Charge de travail par membre"), _("Aucune charge a consolider."))
        body_rows = []
        for row in rows:
            body_rows.extend(
                [
                    "<tr>",
                    "<td>%s</td>" % escape(row["member"]),
                    "<td>%s</td>" % row["assigned"],
                    "<td>%s</td>" % row["in_progress"],
                    "<td>%s</td>" % row["overdue"],
                    "<td>%s</td>" % row["blocked"],
                    "<td>%s</td>" % escape(self._format_hours(row["allocated_hours"])),
                    "<td>%s</td>" % self._render_badge(row["load_level"], row["load_tone"]),
                    "</tr>",
                ]
            )
        return self._render_table_panel(
            title=_("Charge de travail par membre"),
            subtitle=_("Nombre de taches assignees, charge ouverte et niveau de pression par membre"),
            headers=[_("Membre"), _("Assignees"), _("En cours"), _("Retard"), _("Bloquees"), _("Charge"), _("Niveau")],
            rows_html="".join(body_rows),
        )

    def _render_deadline_panel(self, rows):
        if not rows:
            return self._render_empty_panel(_("Deadlines importantes"), _("Aucune deadline imminente."))
        body_rows = []
        for row in rows:
            body_rows.extend(
                [
                    "<tr>",
                    "<td>%s</td>" % self._render_badge(row["kind"], row["tone"]),
                    "<td>%s</td>" % escape(row["label"]),
                    "<td>%s</td>" % escape(row["project"]),
                    "<td>%s</td>" % escape(row["owner"]),
                    "<td>%s</td>" % escape(row["date"]),
                    "</tr>",
                ]
            )
        return self._render_table_panel(
            title=_("Deadlines importantes"),
            subtitle=_("Echeances projet, taches et livrables a traiter en priorite"),
            headers=[_("Type"), _("Element"), _("Projet"), _("Responsable"), _("Date")],
            rows_html="".join(body_rows),
        )

    def _render_deliverable_panel(self, rows):
        if not rows:
            return self._render_empty_panel(_("Livrables et jalons"), _("Aucun livrable dans le perimetre selectionne."))
        body_rows = []
        for row in rows:
            body_rows.extend(
                [
                    "<tr>",
                    "<td>%s</td>" % escape(row["name"]),
                    "<td>%s</td>" % escape(row["project"]),
                    "<td>%s</td>" % escape(row["owner"]),
                    "<td>%s</td>" % self._render_badge(row["status"], row["tone"]),
                    "<td>%s</td>" % escape(row["planned_date"]),
                    "<td>%s</td>" % escape(row["delivered_date"]),
                    "<td>%s</td>" % escape(row["comment"]),
                    "</tr>",
                ]
            )
        return self._render_table_panel(
            title=_("Livrables et jalons"),
            subtitle=_("Suivi des livrables cles avec responsable, date prevue et date reelle"),
            headers=[_("Livrable"), _("Projet"), _("Responsable"), _("Statut"), _("Date prevue"), _("Date reelle"), _("Commentaire")],
            rows_html="".join(body_rows),
        )

    def _render_budget_panel(self, projects):
        palette = self._dashboard_palette()
        if not projects:
            return self._render_empty_panel(_("Budget et ressources"), _("Aucun projet selectionne."))
        lines = [
            (_("Budget prevu (heures)"), self._format_hours(sum(projects.mapped("allocated_hours")))),
            (_("Budget consomme (heures)"), self._format_hours(sum(projects.mapped("digiplus_effective_hours")))),
            (_("Budget restant (heures)"), self._format_hours(sum(projects.mapped("digiplus_remaining_estimated_hours")))),
            (_("Ecart budget (heures)"), self._format_hours(sum(projects.mapped("digiplus_budget_variance_hours")))),
            (_("Heures facturables"), self._format_hours(sum(projects.mapped("digiplus_billable_hours")))),
        ]
        rows_html = "".join(
            "<tr><td>%s</td><td>%s</td></tr>" % (escape(label), escape(value)) for label, value in lines
        )
        note = _(
            "Le module reutilise les indicateurs de budget deja presents dans le projet. Les ressources cloud et services externes pourront etre ajoutes ensuite sans casser l'existant."
        )
        return (
            "<div style=\"{panel_style}\">"
            "<div style=\"font-size:18px;font-weight:800;color:{text};\">{title}</div>"
            "<div style=\"color:{muted};font-size:13px;margin:4px 0 14px;\">{subtitle}</div>"
            "<table style=\"width:100%%;border-collapse:collapse;\">{rows_html}</table>"
            "<div style=\"margin-top:14px;padding:12px 14px;border-radius:14px;background:{surface};color:{muted};font-size:13px;border:1px solid {soft_border};\">{note}</div>"
            "</div>"
        ).format(
            panel_style=self._panel_style(),
            text=palette["text"],
            title=escape(_("Budget et ressources")),
            muted=palette["muted"],
            subtitle=escape(_("Pilotage de la charge et du budget existant du module Projet")),
            rows_html=rows_html,
            surface=palette["surface"],
            soft_border=palette["soft_border"],
            note=escape(note),
        )

    def _render_table_panel(self, title, subtitle, headers, rows_html):
        palette = self._dashboard_palette()
        head_html = "".join(
            "<th style=\"padding:12px 14px;text-align:left;font-size:12px;font-weight:700;color:%s;text-transform:uppercase;letter-spacing:0.03em;border-bottom:1px solid %s;\">%s</th>"
            % (palette["muted"], palette["border"], escape(header))
            for header in headers
        )
        return (
            "<div style=\"{panel_style}\">"
            "<div style=\"font-size:18px;font-weight:800;color:{text};\">{title}</div>"
            "<div style=\"color:{muted};font-size:13px;margin:4px 0 14px;\">{subtitle}</div>"
            "<div style=\"overflow:auto;\">"
            "<table style=\"width:100%%;border-collapse:separate;border-spacing:0;border:1px solid {border};border-radius:14px;overflow:hidden;background:{panel_bg};\">"
            "<thead style=\"background:{surface};\"><tr>{head_html}</tr></thead>"
            "<tbody>{rows_html}</tbody>"
            "</table>"
            "</div>"
            "</div>"
        ).format(
            panel_style=self._panel_style(),
            text=palette["text"],
            title=escape(title),
            muted=palette["muted"],
            subtitle=escape(subtitle),
            border=palette["border"],
            panel_bg=palette["panel_bg"],
            surface=palette["surface"],
            head_html=head_html,
            rows_html=rows_html,
        )

    def _render_empty_panel(self, title, subtitle):
        palette = self._dashboard_palette()
        return (
            "<div style=\"{panel_style}\">"
            "<div style=\"font-size:18px;font-weight:800;color:{text};\">{title}</div>"
            "<div style=\"color:{muted};font-size:13px;margin:4px 0 14px;\">{subtitle}</div>"
            "<div style=\"padding:24px 0;color:{subtle};text-align:center;font-size:13px;\">{empty_label}</div>"
            "</div>"
        ).format(
            panel_style=self._panel_style(),
            text=palette["text"],
            title=escape(title),
            muted=palette["muted"],
            subtitle=escape(subtitle),
            subtle=palette["subtle"],
            empty_label=escape(_("Aucune donnee disponible.")),
        )

    def _get_selection_label(self, field_name, value, record=None):
        target = record or self
        if not value or field_name not in target._fields:
            return "-"
        return dict(target._fields[field_name].selection).get(value, value)

    def _get_nearest_task_deadline(self, tasks):
        deadlines = [value for value in tasks.mapped("digiplus_date_end") + tasks.mapped("date_deadline") if value]
        return min(deadlines) if deadlines else False

    def _get_days_remaining(self, deadline):
        if not deadline:
            return False
        deadline_date = fields.Date.to_date(deadline)
        return (deadline_date - fields.Date.context_today(self)).days

    def _format_date(self, value):
        if not value:
            return "-"
        return fields.Date.to_date(value).strftime("%d/%m/%Y")

    def _format_datetime(self, value):
        if not value:
            return "-"
        localized = fields.Datetime.context_timestamp(self, value)
        return localized.strftime("%d/%m/%Y %H:%M")

    def _format_days_remaining(self, value):
        if value is False:
            return "-"
        if value < 0:
            return _("%s j de retard") % abs(value)
        if value == 0:
            return _("Aujourd'hui")
        return _("%s j") % value

    def _format_hours(self, value):
        return f"{value:.2f} h"

    def _truncate_text(self, value, limit=90):
        plain = (
            value.replace("<p>", " ")
            .replace("</p>", " ")
            .replace("<br>", " ")
            .replace("<br/>", " ")
            .replace("<br />", " ")
            .strip()
        )
        if len(plain) <= limit:
            return plain or "-"
        return "%s..." % plain[:limit].rstrip()

    def _get_tone_from_state(self, state):
        normalized = (state or "").strip().lower()
        if normalized in ("blocked", "bloque"):
            return "danger"
        if normalized in ("late", "en retard"):
            return "danger"
        if normalized in ("planning", "en attente"):
            return "primary"
        if normalized in ("done", "termine", "livre"):
            return "info"
        if normalized in ("watch", "a surveiller", "review", "en revue"):
            return "warning"
        if normalized in ("active", "actif", "normal", "todo", "a faire"):
            return "success"
        return "neutral"

    def _render_badge(self, label, tone):
        palette = self._dashboard_palette()
        styles = {
            name: "background:%s;color:%s;border:1px solid %s;"
            % (self._get_tone_color(name, "background"), palette[name], self._get_tone_color(name, "background"))
            for name in ("success", "warning", "danger", "info", "primary", "neutral")
        }
        return "<span style=\"display:inline-flex;align-items:center;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:700;%s\">%s</span>" % (
            styles.get(tone, styles["neutral"]),
            escape(label or "-"),
        )

    def _get_load_level(self, assigned_count, allocated_hours, overdue_count, blocked_count):
        if blocked_count or overdue_count >= 3 or assigned_count >= 12 or allocated_hours >= 40.0:
            return _("Critique"), "danger"
        if overdue_count >= 1 or assigned_count >= 8 or allocated_hours >= 24.0:
            return _("Elevee"), "warning"
        if assigned_count >= 4 or allocated_hours >= 12.0:
            return _("Normale"), "success"
        return _("Faible"), "neutral"

    def _build_dashboard_action(self):
        self.ensure_one()
        form_view = self.env.ref("digiplus_project.view_digiplus_project_dashboard_form", raise_if_not_found=False)
        views = [(form_view.id, "form")] if form_view else [(False, "form")]
        return {
            "type": "ir.actions.act_window",
            "name": _("Dashboard Projet"),
            "res_model": self._name,
            "view_mode": "form",
            "res_id": self.id,
            "views": views,
            "target": "current",
        }

    @api.model
    def action_open_dashboard(self):
        wizard = self.create({})
        return wizard._build_dashboard_action()

    def action_refresh_dashboard(self):
        self.ensure_one()
        wizard = self.create(
            {
                "period_filter": self.period_filter,
                "date_from": self.date_from,
                "date_to": self.date_to,
                "project_id": self.project_id.id,
                "partner_id": self.partner_id.id,
                "manager_id": self.manager_id.id,
                "status_filter": self.status_filter,
                "priority_filter": self.priority_filter,
                "overdue_only": self.overdue_only,
                "blocked_only": self.blocked_only,
            }
        )
        return wizard._build_dashboard_action()

    def _action_open_projects(self, extra_domain=None):
        self.ensure_one()
        projects = self._get_filtered_projects()
        domain = [("id", "in", projects.ids)] + list(extra_domain or [])
        return {
            "type": "ir.actions.act_window",
            "name": _("Projets"),
            "res_model": "project.project",
            "view_mode": "kanban,list,form,calendar",
            "domain": domain,
            "search_view_id": self.env.ref("project.view_project_project_filter").id,
        }

    def _action_open_tasks(self, extra_domain=None):
        self.ensure_one()
        projects = self._get_filtered_projects()
        domain = [("project_id", "in", projects.ids), ("display_in_project", "=", True)] + list(extra_domain or [])
        return {
            "type": "ir.actions.act_window",
            "name": _("Taches"),
            "res_model": "project.task",
            "view_mode": "list,kanban,form,calendar,pivot,graph",
            "domain": domain,
            "search_view_id": self.env.ref("project.view_task_search_form").id,
            "views": [(self.env.ref("project.open_view_all_tasks_list_view").id, "list")],
        }

    def _action_open_deliverables(self, extra_domain=None):
        self.ensure_one()
        projects = self._get_filtered_projects()
        domain = [("project_id", "in", projects.ids)] + list(extra_domain or [])
        action = self.env["ir.actions.act_window"]._for_xml_id("digiplus_project.action_digiplus_project_deliverables")
        action["domain"] = domain
        return action

    def action_open_projects(self):
        return self._action_open_projects()

    def action_open_overdue_tasks(self):
        return self._action_open_tasks([("digiplus_is_overdue", "=", True), ("state", "not in", CLOSED_TASK_STATES)])

    def action_open_blocked_tasks(self):
        return self._action_open_tasks([("digiplus_is_blocked", "=", True), ("state", "not in", CLOSED_TASK_STATES)])

    def action_open_unassigned_tasks(self):
        return self._action_open_tasks([("user_ids", "=", False), ("state", "not in", CLOSED_TASK_STATES)])

    def action_open_deliverables(self):
        return self._action_open_deliverables()

    def action_create_task(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Nouvelle tache"),
            "res_model": "project.task",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_project_id": self.project_id.id if self.project_id else False,
                "default_user_ids": [self.manager_id.id] if self.manager_id else [],
            },
        }

    def action_create_deliverable(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Nouveau livrable"),
            "res_model": "project.deliverable",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_project_id": self.project_id.id if self.project_id else False,
                "default_responsible_id": self.manager_id.id if self.manager_id else self.env.user.id,
            },
        }

    def action_print_project_report(self):
        self.ensure_one()
        projects = self._get_filtered_projects()
        if len(projects) == 1:
            return projects.action_view_digiplus_progress_report()
        return self._action_open_projects()
