from collections import defaultdict
from datetime import date, timedelta
from math import pi

from markupsafe import Markup, escape

from odoo import _, api, fields, models


class CrmDashboardWizard(models.TransientModel):
    _name = "digiplus.crm.dashboard.wizard"
    _description = "Dashboard CRM DigiPlus"
    _rec_name = "name"
    _transient_max_hours = 72.0

    name = fields.Char(string="Nom", default=lambda self: _("Tableau de bord commercial"), readonly=True)
    period_filter = fields.Selection(
        [
            ("month", "Mois en cours"),
            ("quarter", "Trimestre en cours"),
            ("year", "Annee en cours"),
            ("custom", "Periode personnalisee"),
        ],
        string="Periode",
        default="month",
        required=True,
    )
    date_from = fields.Date(string="Date de debut")
    date_to = fields.Date(string="Date de fin")
    user_id = fields.Many2one("res.users", string="Commercial")
    currency_id = fields.Many2one("res.currency", compute="_compute_currency_id", readonly=True)
    forecast_amount = fields.Monetary(string="CA previsionnel", compute="_compute_metrics")
    conversion_rate = fields.Float(string="Taux de conversion (%)", compute="_compute_metrics")
    opportunity_count = fields.Integer(string="Opportunites", compute="_compute_metrics")
    overdue_activity_count = fields.Integer(string="Relances en retard", compute="_compute_metrics")
    missing_next_action_count = fields.Integer(string="Sans prochaine action", compute="_compute_metrics")
    updated_at_display = fields.Char(string="Mise a jour", compute="_compute_metrics")
    dashboard_html = fields.Html(string="Dashboard", compute="_compute_metrics", sanitize=False)
    kpi_html = fields.Html(string="Indicateurs", compute="_compute_metrics", sanitize=False)
    stage_breakdown_html = fields.Html(string="Pipeline", compute="_compute_metrics", sanitize=False)
    source_breakdown_html = fields.Html(string="Sources", compute="_compute_metrics", sanitize=False)
    salesperson_breakdown_html = fields.Html(string="Commerciaux", compute="_compute_metrics", sanitize=False)

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        start_date, end_date = self._get_range_for_period("month")
        values.setdefault("date_from", start_date)
        values.setdefault("date_to", end_date)
        return values

    @api.onchange("period_filter")
    def _onchange_period_filter(self):
        if self.period_filter == "custom":
            return
        self.date_from, self.date_to = self._get_range_for_period(self.period_filter)

    def _compute_currency_id(self):
        preferred_currency = self.env["res.company"]._get_preferred_display_currency()
        for wizard in self:
            wizard.currency_id = preferred_currency

    @api.depends("period_filter", "date_from", "date_to", "user_id")
    def _compute_metrics(self):
        won_stage = self.env.ref("digiplus_crm.stage_won", raise_if_not_found=False)
        lost_stage = self.env.ref("digiplus_crm.stage_lost", raise_if_not_found=False)
        for wizard in self:
            leads = wizard._get_dashboard_leads()
            summary = wizard._build_summary_metrics(leads, won_stage, lost_stage)
            previous_summary = wizard._build_previous_period_metrics(won_stage, lost_stage)
            updated_at = fields.Datetime.context_timestamp(wizard, fields.Datetime.now())

            wizard.opportunity_count = summary["opportunity_count"]
            wizard.forecast_amount = summary["forecast_amount"]
            wizard.overdue_activity_count = summary["overdue_activity_count"]
            wizard.missing_next_action_count = summary["missing_next_action_count"]
            wizard.conversion_rate = summary["conversion_rate"]
            wizard.updated_at_display = updated_at.strftime("%H:%M") if updated_at else ""

            stage_rows = wizard._build_stage_rows(leads)
            source_rows = wizard._build_source_rows(leads)
            user_rows = wizard._build_user_rows(leads)
            overdue_rows = wizard._build_overdue_rows(leads)
            missing_rows = wizard._build_missing_action_rows(leads)

            wizard.dashboard_html = wizard._render_dashboard(
                summary=summary,
                previous_summary=previous_summary,
                stage_rows=stage_rows,
                source_rows=source_rows,
                user_rows=user_rows,
                overdue_rows=overdue_rows,
                missing_rows=missing_rows,
            )
            wizard.kpi_html = False
            wizard.stage_breakdown_html = False
            wizard.source_breakdown_html = False
            wizard.salesperson_breakdown_html = False

    @api.model
    def _get_range_for_period(self, period_filter):
        today = fields.Date.context_today(self)
        if period_filter == "quarter":
            quarter = ((today.month - 1) // 3) + 1
            start_month = ((quarter - 1) * 3) + 1
            start_date = date(today.year, start_month, 1)
            if start_month == 10:
                end_date = date(today.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(today.year, start_month + 3, 1) - timedelta(days=1)
            return start_date, end_date
        if period_filter == "year":
            return date(today.year, 1, 1), date(today.year, 12, 31)
        start_date = date(today.year, today.month, 1)
        if today.month == 12:
            end_date = date(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
        return start_date, end_date

    def _get_dashboard_lead_domain(self):
        self.ensure_one()
        domain = [("type", "=", "opportunity")]
        if self.user_id:
            domain.append(("user_id", "=", self.user_id.id))
        domain += self._get_dashboard_period_domain()
        return domain

    def _get_dashboard_period_domain(self):
        self.ensure_one()
        if not (self.date_from and self.date_to):
            return []
        start_dt = fields.Datetime.to_datetime(self.date_from)
        end_dt = fields.Datetime.to_datetime(self.date_to) + timedelta(days=1)
        return [
            "|",
            "&",
            ("date_deadline", ">=", self.date_from),
            ("date_deadline", "<=", self.date_to),
            "&",
            "&",
            ("date_deadline", "=", False),
            ("create_date", ">=", start_dt),
            ("create_date", "<", end_dt),
        ]

    def _get_dashboard_leads(self):
        self.ensure_one()
        leads = self.env["crm.lead"].search(self._get_dashboard_lead_domain())
        return leads

    def _get_dashboard_leads_for_period(self, date_from, date_to):
        self.ensure_one()
        domain = [("type", "=", "opportunity")]
        if self.user_id:
            domain.append(("user_id", "=", self.user_id.id))
        if date_from and date_to:
            start_dt = fields.Datetime.to_datetime(date_from)
            end_dt = fields.Datetime.to_datetime(date_to) + timedelta(days=1)
            domain += [
                "|",
                "&",
                ("date_deadline", ">=", date_from),
                ("date_deadline", "<=", date_to),
                "&",
                "&",
                ("date_deadline", "=", False),
                ("create_date", ">=", start_dt),
                ("create_date", "<", end_dt),
            ]
        return self.env["crm.lead"].search(domain)

    def _get_previous_period_range(self):
        self.ensure_one()
        if not (self.date_from and self.date_to):
            return False, False
        duration = (self.date_to - self.date_from).days + 1
        previous_end = self.date_from - timedelta(days=1)
        previous_start = previous_end - timedelta(days=duration - 1)
        return previous_start, previous_end

    def _build_summary_metrics(self, leads, won_stage, lost_stage):
        self.ensure_one()
        won_leads = leads.filtered(lambda lead: won_stage and lead.stage_id == won_stage)
        active_leads = leads.filtered(lambda lead: not lost_stage or lead.stage_id != lost_stage)
        open_leads = active_leads.filtered(lambda lead: not won_stage or lead.stage_id != won_stage)
        return {
            "opportunity_count": len(leads),
            "forecast_amount": sum(active_leads.mapped("expected_revenue")),
            "overdue_activity_count": len(leads.filtered(lambda lead: lead.activity_state == "overdue")),
            "missing_next_action_count": len(leads.filtered("x_missing_next_action")),
            "conversion_rate": (len(won_leads) / len(leads) * 100.0) if leads else 0.0,
            "open_opportunity_count": len(open_leads),
        }

    def _build_previous_period_metrics(self, won_stage, lost_stage):
        self.ensure_one()
        previous_start, previous_end = self._get_previous_period_range()
        if not (previous_start and previous_end):
            return {
                "opportunity_count": 0,
                "forecast_amount": 0.0,
                "overdue_activity_count": 0,
                "missing_next_action_count": 0,
                "conversion_rate": 0.0,
                "open_opportunity_count": 0,
            }
        previous_leads = self._get_dashboard_leads_for_period(previous_start, previous_end)
        return self._build_summary_metrics(previous_leads, won_stage, lost_stage)

    def _build_stage_rows(self, leads):
        self.ensure_one()
        stage_groups = defaultdict(lambda: {"count": 0, "amount": 0.0})
        stage_sequence_map = {
            _("Prospect"): 10,
            _("Qualifié"): 20,
            _("Proposition envoyée"): 30,
            _("Négociation"): 40,
            _("Gagné"): 50,
            _("Perdu"): 60,
        }
        color_map = {
            _("Prospect"): "#12b886",
            _("Qualifié"): "#6bcf63",
            _("Proposition envoyée"): "#3b82f6",
            _("Négociation"): "#8b5cf6",
            _("Gagné"): "#f59e0b",
            _("Perdu"): "#ef4444",
        }
        for lead in leads:
            label = self._normalize_stage_label(lead.stage_id.display_name or _("Sans etape"))
            stage_groups[label]["count"] += 1
            stage_groups[label]["amount"] += lead.expected_revenue or 0.0
        rows = []
        for label, values in sorted(stage_groups.items(), key=lambda item: stage_sequence_map.get(item[0], 999)):
            rows.append(
                {
                    "label": label,
                    "count": values["count"],
                    "amount": values["amount"],
                    "color": color_map.get(label, "#94a3b8"),
                }
            )
        return rows

    def _build_source_rows(self, leads):
        self.ensure_one()
        source_groups = defaultdict(int)
        colors = ["#7c3aed", "#3b82f6", "#8dd36f", "#f59e0b", "#ef4444", "#14b8a6", "#6477a1", "#38bdf8"]
        for lead in leads:
            label = self._normalize_source_label(lead.source_id.display_name or _("Sans source"))
            source_groups[label] += 1
        rows = []
        for index, item in enumerate(sorted(source_groups.items(), key=lambda row: (-row[1], row[0]))):
            label, count = item
            rows.append({"label": label, "count": count, "color": colors[index % len(colors)]})
        return rows

    def _build_user_rows(self, leads):
        self.ensure_one()
        user_groups = defaultdict(lambda: {"count": 0, "amount": 0.0})
        for lead in leads:
            label = self._normalize_salesperson_label(lead.user_id)
            user_groups[label]["count"] += 1
            user_groups[label]["amount"] += lead.expected_revenue or 0.0
        rows = []
        for label, values in sorted(user_groups.items(), key=lambda row: (-row[1]["amount"], -row[1]["count"], row[0])):
            rows.append({"label": label, "count": values["count"], "amount": values["amount"]})
        return rows

    def _build_overdue_rows(self, leads):
        self.ensure_one()
        today = fields.Date.context_today(self)
        rows = []
        overdue_leads = leads.filtered(lambda lead: lead.activity_state == "overdue").sorted(
            key=lambda lead: lead.activity_date_deadline or today
        )
        for lead in overdue_leads[:5]:
            deadline = lead.activity_date_deadline
            late_days = (today - deadline).days if deadline else 0
            rows.append(
                {
                    "opportunity": lead.name,
                    "client": lead.partner_id.name or lead.partner_name or "-",
                    "salesperson": self._normalize_salesperson_label(lead.user_id),
                    "date": self._format_date(deadline),
                    "detail": _("%s j") % late_days if late_days else _("Aujourd'hui"),
                }
            )
        return rows

    def _build_missing_action_rows(self, leads):
        self.ensure_one()
        missing_leads = leads.filtered("x_missing_next_action").sorted(
            key=lambda lead: (-(lead.expected_revenue or 0.0), lead.create_date or fields.Datetime.now())
        )
        rows = []
        for lead in missing_leads[:5]:
            rows.append(
                {
                    "opportunity": lead.name,
                    "client": lead.partner_id.name or lead.partner_name or "-",
                    "salesperson": self._normalize_salesperson_label(lead.user_id),
                    "date": self._format_date(self._get_last_activity_date(lead)),
                    "detail": dict(lead._fields["x_priority_level"].selection).get(lead.x_priority_level, _("A valider")),
                }
            )
        return rows

    def _get_last_activity_date(self, lead):
        self.ensure_one()
        today = fields.Date.context_today(self)
        activities = lead.activity_ids.sorted(key=lambda activity: activity.date_deadline or today)
        if activities:
            return activities[-1].date_deadline
        return lead.create_date.date() if lead.create_date else False

    def _format_currency(self, amount):
        self.ensure_one()
        currency = self.currency_id or self.env["res.company"]._get_preferred_display_currency()
        code = (currency.name or "").upper()
        symbol = currency.symbol or code or ""
        if code in {"XAF", "XOF"}:
            symbol = "FCFA"
        formatted_amount = f"{amount:,.0f}".replace(",", " ")
        if not symbol:
            return formatted_amount
        if code in {"XAF", "XOF"} or getattr(currency, "position", "before") == "after":
            return "%s %s" % (formatted_amount, symbol)
        return "%s %s" % (symbol, formatted_amount)

    def _format_date(self, value):
        if not value:
            return "-"
        return fields.Date.to_date(value).strftime("%d/%m/%Y")

    def _normalize_stage_label(self, label):
        mapping = {
            "new": _("Prospect"),
            "qualified": _("Qualifié"),
            "qualifie": _("Qualifié"),
            "qualifié": _("Qualifié"),
            "proposition": _("Proposition envoyée"),
            "proposal": _("Proposition envoyée"),
            "proposal sent": _("Proposition envoyée"),
            "proposition envoyee": _("Proposition envoyée"),
            "proposition envoyée": _("Proposition envoyée"),
            "negociation": _("Négociation"),
            "négociation": _("Négociation"),
            "won": _("Gagné"),
            "gagne": _("Gagné"),
            "gagné": _("Gagné"),
            "lost": _("Perdu"),
        }
        normalized = (label or "").strip().lower()
        return mapping.get(normalized, label)

    def _normalize_source_label(self, label):
        mapping = {
            "lead recall": _("Relance portefeuille"),
            "newsletter": _("Campagne email"),
            "search engine": _("Recherche web"),
            "phone inquiry": _("Appel entrant"),
            "partner": _("Partenariat"),
            "referral": _("Recommandation"),
            "website": _("Site web"),
        }
        normalized = (label or "").strip().lower()
        return mapping.get(normalized, label)

    def _normalize_salesperson_label(self, user):
        if not user:
            return _("Non assigne")
        if not user.active or "demo" in (user.name or "").lower():
            return _("Portefeuille a reaffecter")
        return user.display_name

    def _render_kpi_cards(self):
        self.ensure_one()
        period_label = dict(self._fields["period_filter"].selection).get(self.period_filter, self.period_filter)
        salesperson_label = self._normalize_salesperson_label(self.user_id) if self.user_id else _("Tous les commerciaux")
        cards = [
            {
                "label": _("CA previsionnel"),
                "value": self._format_currency(self.forecast_amount),
                "hint": period_label,
                "tone": "primary",
            },
            {
                "label": _("Taux de conversion"),
                "value": "%s%%" % f"{self.conversion_rate:.0f}",
                "hint": _("%s opportunites") % self.opportunity_count,
                "tone": "success",
            },
            {
                "label": _("Relances en retard"),
                "value": str(self.overdue_activity_count),
                "hint": _("A traiter aujourd'hui"),
                "tone": "danger" if self.overdue_activity_count else "neutral",
            },
            {
                "label": _("Sans prochaine action"),
                "value": str(self.missing_next_action_count),
                "hint": salesperson_label,
                "tone": "warning" if self.missing_next_action_count else "neutral",
            },
        ]
        tone_styles = {
            "primary": "background:linear-gradient(135deg,#edf8f5 0%,#ffffff 100%);color:#0f5132;",
            "success": "background:linear-gradient(135deg,#ecfdf3 0%,#ffffff 100%);color:#166534;",
            "warning": "background:linear-gradient(135deg,#fff7ed 0%,#ffffff 100%);color:#b45309;",
            "danger": "background:linear-gradient(135deg,#fff1f2 0%,#ffffff 100%);color:#be123c;",
            "neutral": "background:linear-gradient(135deg,#f8fafc 0%,#ffffff 100%);color:#334155;",
        }
        html = [
            "<div style=\"background:linear-gradient(180deg,#fbfcfd 0%,#f3f7f8 100%);"
            "border:1px solid rgba(16,53,62,0.08);border-radius:22px;padding:20px 22px;"
            "box-shadow:0 12px 30px rgba(16,53,62,0.06);margin-bottom:16px;\">",
            "<div style=\"display:flex;justify-content:space-between;align-items:flex-end;gap:16px;"
            "flex-wrap:wrap;margin-bottom:18px;\">",
            "<div>",
            "<h2 style=\"margin:0 0 4px;color:#10353e;font-size:24px;font-weight:700;\">"
            "Tableau de bord commercial</h2>",
            "<p style=\"margin:0;color:#58717a;font-size:14px;\">Periode: %s</p>" % escape(period_label),
            "</div>",
            "<div style=\"margin:0;color:#58717a;font-size:14px;font-weight:600;\">%s</div>"
            % escape(salesperson_label),
            "</div>",
            "<div style=\"display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;\">",
        ]
        for card in cards:
            card_style = tone_styles[card["tone"]]
            html.extend(
                [
                    "<div style=\"border:1px solid rgba(16,53,62,0.08);border-radius:18px;"
                    "padding:16px 18px;box-shadow:0 12px 30px rgba(16,53,62,0.06);%s\">"
                    % card_style,
                    "<div style=\"color:#5b7278;font-size:12px;text-transform:uppercase;"
                    "letter-spacing:0.04em;margin-bottom:8px;\">%s</div>" % escape(card["label"]),
                    "<div style=\"color:#0f172a;font-size:28px;font-weight:700;line-height:1.1;\">%s</div>"
                    % escape(card["value"]),
                    "<div style=\"color:#6b7f86;font-size:14px;margin-top:8px;\">%s</div>"
                    % escape(card["hint"]),
                    "</div>",
                ]
            )
        html.append("</div></div>")
        return Markup("".join(html))

    def _render_bar_section(self, title, subtitle, rows, monetary=False, value_mode="count", tone="primary"):
        self.ensure_one()
        if not rows:
            return Markup(
                "<div style=\"border:1px solid rgba(16,53,62,0.08);border-radius:18px;background:#ffffff;"
                "padding:18px 20px;box-shadow:0 12px 30px rgba(16,53,62,0.06);margin-bottom:16px;\">"
                "<div style=\"padding:16px 4px;color:#6a7f86;text-align:center;\">%s</div></div>"
            ) % escape(_("Aucune donnee disponible pour ce filtre."))
        gradients = {
            "stage": "linear-gradient(90deg,#0b7c59 0%,#13b68f 100%)",
            "salesperson": "linear-gradient(90deg,#0f4c81 0%,#3c8dbc 100%)",
            "source": "linear-gradient(90deg,#b45309 0%,#f59e0b 100%)",
            "primary": "linear-gradient(90deg,#0b7c59 0%,#13b68f 100%)",
        }
        if value_mode == "amount":
            max_value = max((row[-1] or 0.0) for row in rows) or 1.0
        else:
            max_value = max((row[1] or 0.0) for row in rows) or 1.0
        total_count = sum((row[1] or 0) for row in rows) or 1
        html = [
            "<div style=\"border:1px solid rgba(16,53,62,0.08);border-radius:18px;background:#ffffff;"
            "padding:18px 20px;box-shadow:0 12px 30px rgba(16,53,62,0.06);margin-bottom:16px;\">",
            "<div style=\"display:flex;justify-content:space-between;align-items:center;gap:12px;"
            "margin-bottom:14px;flex-wrap:wrap;\">",
            "<div><h3 style=\"margin:0;color:#10353e;font-size:18px;font-weight:700;\">%s</h3>"
            "<p style=\"margin:4px 0 0;color:#678089;font-size:14px;\">%s</p></div>"
            % (escape(title), escape(subtitle)),
            "</div>",
            "<div>",
        ]
        for row in rows:
            label = row[0]
            count = row[1] if len(row) > 1 else 0
            amount = row[2] if len(row) > 2 else 0.0
            primary_value = amount if value_mode == "amount" else count
            width = max(8, round((primary_value / max_value) * 100)) if max_value else 8
            if monetary and len(row) > 2:
                right_value = self._format_currency(amount)
                hint = _("%s opportunites") % count
            else:
                percentage = round((count / total_count) * 100)
                right_value = _("%s%%") % percentage
                hint = _("%s opportunites") % count
            html.extend(
                [
                    "<div style=\"display:flex;flex-direction:column;gap:6px;margin-bottom:14px;\">",
                    "<div style=\"display:flex;justify-content:space-between;gap:14px;align-items:baseline;"
                    "flex-wrap:wrap;\">",
                    "<div style=\"color:#173640;font-weight:600;\">%s</div>" % escape(label),
                    "<div style=\"display:flex;gap:12px;color:#607983;font-size:13px;align-items:baseline;\">"
                    "<span>%s</span><strong style=\"color:#0f172a;font-size:14px;\">%s</strong></div>"
                    % (escape(hint), escape(right_value)),
                    "</div>",
                    "<div style=\"width:100%;height:12px;background:#edf3f4;border-radius:999px;"
                    "overflow:hidden;\">",
                    "<div style=\"width:%s%%;height:100%%;border-radius:999px;background:%s;\"></div>"
                    % (width, gradients.get(tone, gradients["primary"])),
                    "</div>",
                    "</div>",
                ]
            )
        html.append("</div></div>")
        return Markup("".join(html))

    def _format_delta(self, current, previous, mode="count"):
        self.ensure_one()
        delta = current - previous
        if mode == "money":
            value = self._format_currency(abs(delta))
        elif mode == "rate":
            value = "%s pts" % abs(round(delta))
        else:
            value = str(abs(round(delta)))
        if not previous and not delta:
            return {"label": _("Stable"), "color": "#64748b"}
        if delta > 0:
            return {"label": "+ %s" % value, "color": "#16a34a"}
        if delta < 0:
            return {"label": "- %s" % value, "color": "#dc2626"}
        return {"label": _("Stable"), "color": "#64748b"}

    def _render_dashboard(self, summary, previous_summary, stage_rows, source_rows, user_rows, overdue_rows, missing_rows):
        self.ensure_one()
        html = [
            "<div class=\"dp-crm-dashboard-content\" style=\"display:flex;flex-direction:column;gap:20px;\">",
            self._render_metric_cards(summary, previous_summary),
            "<div class=\"dp-crm-dashboard-analytics-grid\" style=\"display:grid;grid-template-columns:1.15fr 1fr 1.1fr;gap:16px;align-items:start;\">",
            self._render_pipeline_panel(stage_rows, summary),
            self._render_sales_panel(user_rows, summary),
            self._render_source_panel(source_rows),
            "</div>",
            "<div class=\"dp-crm-dashboard-followup-grid\" style=\"display:grid;grid-template-columns:1fr 1fr;gap:18px;align-items:start;\">",
            self._render_followup_panel(
                title=_("Relances en retard"),
                subtitle=_("Opportunites a traiter rapidement"),
                rows=overdue_rows,
                detail_title=_("Retard"),
                empty_label=_("Aucune relance en retard sur la periode."),
                accent="#ef4444",
                badge_value=summary["overdue_activity_count"],
            ),
            self._render_followup_panel(
                title=_("Opportunites sans prochaine action"),
                subtitle=_("Relances a planifier pour securiser le pipeline"),
                rows=missing_rows,
                detail_title=_("Priorite"),
                empty_label=_("Toutes les opportunites ont une prochaine action."),
                accent="#f59e0b",
                badge_value=summary["missing_next_action_count"],
            ),
            "</div>",
            "</div>",
        ]
        return Markup("".join(html))

    def _render_dashboard_header(self):
        self.ensure_one()
        period_label = dict(self._fields["period_filter"].selection).get(self.period_filter, self.period_filter)
        salesperson_label = self._normalize_salesperson_label(self.user_id) if self.user_id else _("Tous les commerciaux")
        updated_at = self.updated_at_display or ""
        return (
            "<div class=\"dp-crm-dashboard-header\" style=\"display:flex;justify-content:space-between;gap:16px;align-items:flex-start;flex-wrap:wrap;\">"
            "<div>"
            "<div style=\"color:#1f2a60;font-size:16px;font-weight:800;margin-bottom:4px;\">Tableau de bord commercial</div>"
            "<div style=\"color:#64748b;font-size:13px;\">Vue d'ensemble des opportunites et de la performance commerciale.</div>"
            "</div>"
            "<div class=\"dp-crm-dashboard-header-meta\" style=\"display:flex;gap:12px;align-items:center;flex-wrap:wrap;\">"
            "<div class=\"dp-crm-dashboard-chip\" style=\"padding:10px 14px;border:1px solid #e2e8f0;border-radius:12px;background:#ffffff;color:#334155;"
            "font-size:13px;font-weight:600;\">Periode : %s</div>"
            "<div class=\"dp-crm-dashboard-chip\" style=\"padding:10px 14px;border:1px solid #e2e8f0;border-radius:12px;background:#ffffff;color:#334155;"
            "font-size:13px;font-weight:600;\">%s</div>"
            "<div style=\"color:#64748b;font-size:12px;\">Mise a jour : %s</div>"
            "</div>"
            "</div>"
        ) % (escape(period_label), escape(salesperson_label), escape(updated_at))

    def _render_metric_cards(self, summary, previous_summary):
        self.ensure_one()
        cards = [
            {
                "label": _("CA previsionnel"),
                "value": self._format_currency(summary["forecast_amount"]),
                "hint": dict(self._fields["period_filter"].selection).get(self.period_filter, self.period_filter),
                "delta": self._format_delta(summary["forecast_amount"], previous_summary["forecast_amount"], mode="money"),
                "delta_mode": "default",
                "accent_color": "#18b368",
                "icon_bg": "#dff7ee",
                "icon_color": "#16a34a",
                "icon_html": "<i class='fa fa-money'></i>",
            },
            {
                "label": _("Taux de conversion"),
                "value": "%s%%" % round(summary["conversion_rate"]),
                "hint": _("%s opportunites") % summary["opportunity_count"],
                "delta": self._format_delta(summary["conversion_rate"], previous_summary["conversion_rate"], mode="rate"),
                "delta_mode": "default",
                "accent_color": "#16a34a",
                "icon_bg": "#e6f9df",
                "icon_color": "#16a34a",
                "icon_html": "<i class='fa fa-percent'></i>",
            },
            {
                "label": _("Relances en retard"),
                "value": str(summary["overdue_activity_count"]),
                "hint": _("A traiter aujourd'hui"),
                "delta": self._format_delta(summary["overdue_activity_count"], previous_summary["overdue_activity_count"]),
                "delta_mode": "accent",
                "accent_color": "#ff4d4f",
                "icon_bg": "#ffe8e8",
                "icon_color": "#ff4d4f",
                "icon_html": "<i class='fa fa-exclamation-triangle'></i>",
            },
            {
                "label": _("Sans prochaine action"),
                "value": str(summary["missing_next_action_count"]),
                "hint": _("A securiser"),
                "delta": self._format_delta(summary["missing_next_action_count"], previous_summary["missing_next_action_count"]),
                "delta_mode": "accent",
                "accent_color": "#f59e0b",
                "icon_bg": "#fff4db",
                "icon_color": "#f59e0b",
                "icon_html": "<i class='fa fa-clock-o'></i>",
            },
            {
                "label": _("Opportunites ouvertes"),
                "value": str(summary["open_opportunity_count"]),
                "hint": _("Tous les stades actifs"),
                "delta": self._format_delta(summary["open_opportunity_count"], previous_summary["open_opportunity_count"]),
                "delta_mode": "accent",
                "accent_color": "#7c3aed",
                "icon_bg": "#efe8ff",
                "icon_color": "#7c3aed",
                "icon_html": "<i class='fa fa-crosshairs'></i>",
            },
        ]
        html = ["<div class=\"dp-crm-dashboard-metrics\" style=\"display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:16px;\">"]
        for card in cards:
            delta_color = card["delta"]["color"]
            if card["delta_mode"] == "accent" and card["delta"]["label"] != _("Stable"):
                delta_color = card["accent_color"]
            html.extend(
                [
                    "<div class=\"dp-crm-dashboard-card\" style=\"border:1px solid #e6ebf2;border-radius:18px;background:#ffffff;padding:16px;"
                    "box-shadow:0 10px 30px rgba(51,65,85,0.06);\">",
                    "<div style=\"display:flex;justify-content:space-between;gap:12px;align-items:flex-start;\">",
                    "<div style=\"width:54px;height:54px;border-radius:14px;background:%s;display:flex;align-items:center;"
                    "justify-content:center;color:%s;font-size:24px;font-weight:800;\">%s</div>"
                    % (card["icon_bg"], card["icon_color"], card["icon_html"]),
                    "<div style=\"flex:1;\">",
                    "<div style=\"color:#475569;font-size:14px;margin-bottom:8px;\">%s</div>" % escape(card["label"]),
                    "<div style=\"color:#0f172a;font-size:22px;font-weight:800;line-height:1.1;\">%s</div>"
                    % escape(card["value"]),
                    "</div>",
                    "</div>",
                    "<div style=\"display:flex;justify-content:space-between;gap:10px;margin-top:14px;align-items:center;\">",
                    "<div style=\"color:#64748b;font-size:13px;\">%s</div>" % escape(card["hint"]),
                    "<div style=\"color:%s;font-size:13px;font-weight:700;\">%s</div>"
                    % (delta_color, escape(card["delta"]["label"])),
                    "</div>",
                    "</div>",
                ]
            )
        html.append("</div>")
        return "".join(html)

    def _render_pipeline_panel(self, stage_rows, summary):
        self.ensure_one()
        if not stage_rows:
            return self._render_empty_panel(
                title=_("Pipeline commercial"),
                subtitle=_("Aucune opportunite sur la periode."),
                empty_label=_("Le pipeline s'affichera ici des que des opportunites seront disponibles."),
            )
        rows_html = []
        total_count = summary["opportunity_count"] or 1
        for row in stage_rows:
            rows_html.extend(
                [
                    "<div class=\"dp-crm-dashboard-pipeline-row\" style=\"display:grid;grid-template-columns:18px 1fr 92px 128px;gap:10px;align-items:center;"
                    "padding:9px 0;border-bottom:1px solid #eef2f7;\">",
                    "<span style=\"width:10px;height:10px;border-radius:999px;background:%s;\"></span>" % row["color"],
                    "<div>",
                    "<div style=\"color:#1e293b;font-size:14px;font-weight:700;\">%s</div>" % escape(row["label"]),
                    "<div style=\"color:#64748b;font-size:12px;\">%s%%</div>" % round((row["count"] / total_count) * 100),
                    "</div>",
                    "<div style=\"color:#1e293b;font-size:14px;font-weight:700;text-align:center;\">%s</div>" % row["count"],
                    "<div style=\"color:#1e293b;font-size:14px;font-weight:700;text-align:right;\">%s</div>"
                    % escape(self._format_currency(row["amount"])),
                    "</div>",
                ]
            )
        rows_html.extend(
            [
                "<div class=\"dp-crm-dashboard-pipeline-row dp-crm-dashboard-pipeline-total\" style=\"display:grid;grid-template-columns:18px 1fr 92px 128px;gap:10px;align-items:center;"
                "padding:11px 0 0;border-top:1px solid #dbe3ed;margin-top:8px;\">",
                "<span></span>",
                "<div style=\"color:#1e293b;font-size:14px;font-weight:800;\">Total</div>",
                "<div style=\"color:#1e293b;font-size:14px;font-weight:800;text-align:center;\">%s</div>" % summary["opportunity_count"],
                "<div style=\"color:#1e293b;font-size:14px;font-weight:800;text-align:right;\">%s</div>"
                % escape(self._format_currency(summary["forecast_amount"])),
                "</div>",
            ]
        )
        return (
            "<div class=\"dp-crm-dashboard-panel\" style=\"border:1px solid #e6ebf2;border-radius:22px;background:#ffffff;padding:18px 18px 20px;"
            "box-shadow:0 12px 30px rgba(51,65,85,0.06);\">"
            "<div class=\"dp-crm-dashboard-panel-head\" style=\"display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:14px;\">"
            "<div><div style=\"color:#312e81;font-size:16px;font-weight:800;\">Pipeline commercial</div>"
            "<div style=\"color:#64748b;font-size:13px;margin-top:4px;\">%s opportunites pour %s</div></div>"
            "</div>"
            "<div class=\"dp-crm-dashboard-pipeline-grid\" style=\"display:grid;grid-template-columns:280px 1fr;gap:20px;align-items:center;\">"
            "<div class=\"dp-crm-dashboard-svg-box dp-crm-dashboard-chart-box\">%s</div>"
            "<div class=\"dp-crm-dashboard-pipeline-table-wrap\">"
            "<div class=\"dp-crm-dashboard-pipeline-head\" style=\"display:grid;grid-template-columns:1fr 92px 128px;gap:10px;color:#475569;font-size:13px;"
            "font-weight:700;border-bottom:1px solid #dbe3ed;padding-bottom:8px;margin-bottom:2px;\">"
            "<div>Etape</div><div style=\"text-align:center;\">Opportunites</div><div style=\"text-align:right;\">Montant estime</div>"
            "</div>"
            "%s"
            "</div>"
            "</div>"
            "</div>"
        ) % (
            summary["opportunity_count"],
            escape(self._format_currency(summary["forecast_amount"])),
            self._render_funnel_svg(stage_rows),
            "".join(rows_html),
        )

    def _render_funnel_svg(self, stage_rows):
        self.ensure_one()
        if not stage_rows:
            return "<div style=\"color:#64748b;font-size:13px;\">Aucune donnee.</div>"
        width = 230
        center = 120
        segment_height = 44
        min_width = 54
        decrement = (width - min_width) / max(len(stage_rows), 1)
        polygons = [
            "<svg class='dp-crm-dashboard-funnel' viewBox='0 0 240 %s' width='220' height='%s' aria-label='Pipeline'>"
            % (max(250, len(stage_rows) * segment_height + 26), max(250, len(stage_rows) * segment_height + 26))
        ]
        for index, row in enumerate(stage_rows):
            top_width = width - (index * decrement)
            bottom_width = width - ((index + 1) * decrement)
            if index == len(stage_rows) - 1:
                bottom_width = max(24, bottom_width * 0.5)
            y_top = 14 + (index * segment_height)
            y_bottom = y_top + segment_height - 4
            x1 = center - (top_width / 2)
            x2 = center + (top_width / 2)
            x3 = center + (bottom_width / 2)
            x4 = center - (bottom_width / 2)
            polygons.append(
                "<polygon points='%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f' fill='%s' opacity='0.96'/>"
                % (x1, y_top, x2, y_top, x3, y_bottom, x4, y_bottom, row["color"])
            )
        polygons.append("</svg>")
        return "".join(polygons)

    def _render_sales_panel(self, user_rows, summary):
        self.ensure_one()
        if not user_rows:
            return self._render_empty_panel(
                title=_("Performance commerciale"),
                subtitle=_("Par commercial"),
                empty_label=_("Aucune donnee commerciale sur la periode."),
            )
        max_count = max(row["count"] for row in user_rows) or 1
        rows_html = []
        for row in user_rows[:6]:
            count_width = max(10, round((row["count"] / max_count) * 100))
            rows_html.extend(
                [
                    "<div class=\"dp-crm-dashboard-sales-row\" style=\"display:grid;grid-template-columns:minmax(150px,1fr) minmax(180px,1fr) 130px;gap:12px;align-items:center;"
                    "padding:10px 0;border-bottom:1px solid #eef2f7;\">",
                    "<div style=\"color:#334155;font-size:13px;font-weight:600;\">%s</div>" % escape(row["label"]),
                    "<div style=\"display:flex;align-items:center;gap:12px;\">"
                    "<div style=\"min-width:22px;color:#1e293b;font-size:14px;font-weight:700;\">%s</div>" % row["count"] +
                    "<div style=\"flex:1;height:16px;background:#ede9fe;border-radius:999px;overflow:hidden;\">"
                    "<div style=\"width:%s%%;height:100%%;background:linear-gradient(90deg,#5b34d6 0%%,#7c3aed 100%%);\"></div>"
                    % count_width +
                    "</div>",
                    "</div>",
                    "<div style=\"color:#1e293b;font-size:14px;font-weight:700;text-align:right;\">%s</div>"
                    % escape(self._format_currency(row["amount"])),
                    "</div>",
                ]
            )
        rows_html.extend(
            [
                "<div class=\"dp-crm-dashboard-sales-row dp-crm-dashboard-sales-total\" style=\"display:grid;grid-template-columns:minmax(150px,1fr) minmax(180px,1fr) 130px;gap:12px;align-items:center;"
                "padding:12px 0 0;border-top:1px solid #dbe3ed;margin-top:8px;\">",
                "<div style=\"color:#1e293b;font-size:14px;font-weight:800;\">Total</div>",
                "<div style=\"color:#1e293b;font-size:14px;font-weight:800;\">%s</div>" % summary["opportunity_count"],
                "<div style=\"color:#1e293b;font-size:14px;font-weight:800;text-align:right;\">%s</div>"
                % escape(self._format_currency(summary["forecast_amount"])),
                "</div>",
            ]
        )
        return (
            "<div class=\"dp-crm-dashboard-panel\" style=\"border:1px solid #e6ebf2;border-radius:22px;background:#ffffff;padding:18px 18px 20px;"
            "box-shadow:0 12px 30px rgba(51,65,85,0.06);\">"
            "<div class=\"dp-crm-dashboard-panel-head\" style=\"display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:14px;\">"
            "<div><div style=\"color:#312e81;font-size:16px;font-weight:800;\">Performance commerciale</div>"
            "<div style=\"color:#64748b;font-size:13px;margin-top:4px;\">Par commercial</div></div>"
            "<div class=\"dp-crm-dashboard-filter-tag\">Par commercial</div>"
            "</div>"
            "<div class=\"dp-crm-dashboard-sales-head\" style=\"display:grid;grid-template-columns:minmax(150px,1fr) minmax(180px,1fr) 130px;gap:12px;color:#475569;font-size:12px;"
            "font-weight:700;border-bottom:1px solid #dbe3ed;padding-bottom:8px;\">"
            "<div>Commercial</div><div>Opportunites</div><div style=\"text-align:right;\">Montant estime</div>"
            "</div>"
            "%s"
            "</div>"
        ) % "".join(rows_html)

    def _render_source_panel(self, source_rows):
        self.ensure_one()
        if not source_rows:
            return self._render_empty_panel(
                title=_("Origine des opportunites"),
                subtitle=_("Repartition par canal d'acquisition"),
                empty_label=_("Aucune source disponible sur la periode."),
            )
        total = sum(row["count"] for row in source_rows) or 1
        legend_rows = []
        for row in source_rows[:7]:
            percentage = round((row["count"] / total) * 100)
            legend_rows.extend(
                [
                    "<div class=\"dp-crm-dashboard-source-row\" style=\"display:grid;grid-template-columns:14px 1fr auto;gap:10px;align-items:center;"
                    "padding:8px 0;border-bottom:1px solid #eef2f7;\">",
                    "<span style=\"width:12px;height:12px;border-radius:999px;background:%s;\"></span>" % row["color"],
                    "<div style=\"color:#334155;font-size:13px;font-weight:600;\">%s</div>" % escape(row["label"]),
                    "<div style=\"color:#475569;font-size:13px;\">%s (%s%%)</div>" % (row["count"], percentage),
                    "</div>",
                ]
            )
        return (
            "<div class=\"dp-crm-dashboard-panel\" style=\"border:1px solid #e6ebf2;border-radius:22px;background:#ffffff;padding:18px 18px 20px;"
            "box-shadow:0 12px 30px rgba(51,65,85,0.06);\">"
            "<div class=\"dp-crm-dashboard-panel-head\" style=\"display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:14px;\">"
            "<div><div style=\"color:#312e81;font-size:16px;font-weight:800;\">Origine des opportunites</div>"
            "<div style=\"color:#64748b;font-size:13px;margin-top:4px;\">Repartition par canal d'acquisition</div></div>"
            "<div class=\"dp-crm-dashboard-filter-tag\">Par canal d'acquisition</div>"
            "</div>"
            "<div class=\"dp-crm-dashboard-source-grid\" style=\"display:grid;grid-template-columns:220px 1fr;gap:18px;align-items:center;\">"
            "<div class=\"dp-crm-dashboard-svg-box dp-crm-dashboard-chart-box\">%s</div>"
            "<div>%s</div>"
            "</div>"
            "</div>"
        ) % (self._render_donut_svg(source_rows, total), "".join(legend_rows))

    def _render_donut_svg(self, source_rows, total):
        self.ensure_one()
        radius = 74
        circumference = 2 * pi * radius
        offset = 0.0
        parts = [
            "<svg class='dp-crm-dashboard-donut' viewBox='0 0 240 240' width='220' height='220' aria-label='Sources'>",
            "<circle cx='120' cy='120' r='%s' fill='none' stroke='#eef2f7' stroke-width='28'></circle>" % radius,
        ]
        for row in source_rows:
            length = circumference * (row["count"] / total)
            parts.append(
                "<circle cx='120' cy='120' r='%s' fill='none' stroke='%s' stroke-width='28'"
                " stroke-linecap='butt' stroke-dasharray='%.2f %.2f' stroke-dashoffset='%.2f'"
                " transform='rotate(-90 120 120)'></circle>"
                % (radius, row["color"], length, circumference - length, -offset)
            )
            offset += length
        parts.extend(
            [
                "<circle cx='120' cy='120' r='54' fill='#ffffff'></circle>",
                "<text x='120' y='112' text-anchor='middle' style='font-size:34px;font-weight:800;fill:#1e293b;'>%s</text>"
                % total,
                "<text x='120' y='138' text-anchor='middle' style='font-size:15px;fill:#64748b;'>Opportunites</text>",
                "</svg>",
            ]
        )
        return "".join(parts)

    def _render_followup_panel(self, title, subtitle, rows, detail_title, empty_label, accent, badge_value):
        self.ensure_one()
        if not rows:
            return self._render_empty_panel(title=title, subtitle=subtitle, empty_label=empty_label)
        body_rows = []
        for row in rows:
            body_rows.extend(
                [
                    "<tr>",
                    "<td style=\"padding:12px 10px;color:#1e293b;font-size:13px;font-weight:700;\">%s</td>"
                    % escape(row["opportunity"]),
                    "<td style=\"padding:12px 10px;color:#475569;font-size:13px;\">%s</td>" % escape(row["client"]),
                    "<td style=\"padding:12px 10px;color:#475569;font-size:13px;\">%s</td>"
                    % escape(row["salesperson"]),
                    "<td style=\"padding:12px 10px;color:#475569;font-size:13px;\">%s</td>" % escape(row["date"]),
                    "<td style=\"padding:12px 10px;color:%s;font-size:13px;font-weight:700;\">%s</td>"
                    % (accent, escape(row["detail"])),
                    "</tr>",
                ]
            )
        return (
            "<div class=\"dp-crm-dashboard-panel\" style=\"border:1px solid #e6ebf2;border-radius:22px;background:#ffffff;padding:18px 18px 20px;"
            "box-shadow:0 12px 30px rgba(51,65,85,0.06);\">"
            "<div style=\"display:flex;justify-content:space-between;align-items:center;gap:10px;\">"
            "<div style=\"color:#312e81;font-size:16px;font-weight:800;\">%s</div>"
            "<div style=\"padding:4px 10px;border-radius:999px;background:#f8fafc;color:%s;font-size:12px;font-weight:800;\">%s</div>"
            "</div>"
            "<div style=\"color:#64748b;font-size:13px;margin:4px 0 14px;\">%s</div>"
            "<div class=\"dp-crm-dashboard-table-wrap\">"
            "<table class=\"dp-crm-dashboard-table\" style=\"width:100%%;border-collapse:separate;border-spacing:0;border:1px solid #e6ebf2;border-radius:14px;overflow:hidden;\">"
            "<thead style=\"background:#f8fafc;\">"
            "<tr>"
            "<th style=\"text-align:left;padding:12px 10px;color:#475569;font-size:12px;\">Opportunite</th>"
            "<th style=\"text-align:left;padding:12px 10px;color:#475569;font-size:12px;\">Client</th>"
            "<th style=\"text-align:left;padding:12px 10px;color:#475569;font-size:12px;\">Commercial</th>"
            "<th style=\"text-align:left;padding:12px 10px;color:#475569;font-size:12px;\">Date</th>"
            "<th style=\"text-align:left;padding:12px 10px;color:#475569;font-size:12px;\">%s</th>"
            "</tr>"
            "</thead>"
            "<tbody>%s</tbody>"
            "</table>"
            "</div>"
            "<div class=\"dp-crm-dashboard-panel-foot\" style=\"display:flex;justify-content:flex-end;padding-top:14px;\">"
            "<span style=\"color:#6d42ef;font-size:13px;font-weight:700;\">Voir tout <i class='fa fa-arrow-right'></i></span>"
            "</div>"
            "</div>"
        ) % (escape(title), accent, badge_value, escape(subtitle), escape(detail_title), "".join(body_rows))

    def _render_empty_panel(self, title, subtitle, empty_label):
        self.ensure_one()
        return (
            "<div class=\"dp-crm-dashboard-panel\" style=\"border:1px solid #e6ebf2;border-radius:22px;background:#ffffff;padding:18px 18px 20px;"
            "box-shadow:0 12px 30px rgba(51,65,85,0.06);min-height:220px;\">"
            "<div style=\"color:#312e81;font-size:16px;font-weight:800;\">%s</div>"
            "<div style=\"color:#64748b;font-size:13px;margin:4px 0 14px;\">%s</div>"
            "<div style=\"height:160px;display:flex;align-items:center;justify-content:center;color:#64748b;font-size:13px;\">%s</div>"
            "</div>"
        ) % (escape(title), escape(subtitle), escape(empty_label))

    def _get_dashboard_report_payload(self):
        self.ensure_one()
        won_stage = self.env.ref("digiplus_crm.stage_won", raise_if_not_found=False)
        lost_stage = self.env.ref("digiplus_crm.stage_lost", raise_if_not_found=False)
        leads = self._get_dashboard_leads()
        generated_at = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        return {
            "summary": self._build_summary_metrics(leads, won_stage, lost_stage),
            "previous_summary": self._build_previous_period_metrics(won_stage, lost_stage),
            "stage_rows": self._build_stage_rows(leads),
            "source_rows": self._build_source_rows(leads),
            "user_rows": self._build_user_rows(leads),
            "overdue_rows": self._build_overdue_rows(leads),
            "missing_rows": self._build_missing_action_rows(leads),
            "period_label": dict(self._fields["period_filter"].selection).get(self.period_filter, self.period_filter),
            "salesperson_label": self._normalize_salesperson_label(self.user_id) if self.user_id else _("Tous les commerciaux"),
            "date_from": self._format_date(self.date_from),
            "date_to": self._format_date(self.date_to),
            "generated_at": generated_at.strftime("%d/%m/%Y %H:%M") if generated_at else "",
        }

    def action_refresh_dashboard(self):
        self.ensure_one()
        wizard = self.create(
            {
                "period_filter": self.period_filter,
                "date_from": self.date_from,
                "date_to": self.date_to,
                "user_id": self.user_id.id,
            }
        )
        return wizard._build_dashboard_action()

    def action_export_dashboard_report(self):
        self.ensure_one()
        report = self.env.ref("digiplus_crm.action_report_crm_dashboard", raise_if_not_found=False)
        return report.report_action(self) if report else False

    def _build_dashboard_action(self):
        self.ensure_one()
        form_view = self.env.ref("digiplus_crm.view_digiplus_crm_dashboard_form", raise_if_not_found=False)
        views = [(form_view.id, "form")] if form_view else [(False, "form")]
        return {
            "type": "ir.actions.act_window",
            "name": _("Tableau de bord commercial"),
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

    def _action_open_leads(self, extra_domain):
        self.ensure_one()
        domain = self._get_dashboard_lead_domain() + list(extra_domain)
        kanban_view = self.env.ref("digiplus_crm.view_digiplus_crm_lead_kanban_v2", raise_if_not_found=False)
        list_view = self.env.ref("digiplus_crm.view_digiplus_crm_lead_list", raise_if_not_found=False)
        form_view = self.env.ref("digiplus_crm.view_digiplus_crm_lead_form", raise_if_not_found=False)
        search_view = self.env.ref("digiplus_crm.view_digiplus_crm_lead_search", raise_if_not_found=False)
        prospect_stage = self.env.ref("digiplus_crm.stage_prospect", raise_if_not_found=False)
        views = []
        for view in (kanban_view, list_view, form_view):
            if view:
                mode = "kanban" if view == kanban_view else "list" if view == list_view else "form"
                views.append((view.id, mode))
        return {
            "type": "ir.actions.act_window",
            "name": "Opportunites CRM",
            "res_model": "crm.lead",
            "view_mode": "kanban,list,form,graph,pivot",
            "domain": domain,
            "context": {
                "default_type": "opportunity",
                "default_stage_id": prospect_stage.id if prospect_stage else False,
            },
            "views": views,
            "search_view_id": search_view.id if search_view else False,
        }

    def action_open_pipeline(self):
        return self._action_open_leads([])

    def action_open_overdue(self):
        return self._action_open_leads([("activity_state", "=", "overdue")])

    def action_open_missing_next_action(self):
        return self._action_open_leads([("x_missing_next_action", "=", True)])
