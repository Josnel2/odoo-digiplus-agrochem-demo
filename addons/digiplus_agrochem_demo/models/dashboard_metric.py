from odoo import fields, models


METRIC_SELECTION = [
    ("crm", "CRM"),
    ("sales", "Commercial"),
    ("marketing", "Marketing"),
    ("stock", "Stock"),
    ("purchase", "Achats"),
    ("projection", "Reporting & BI"),
]

TREND_SELECTION = [
    ("up", "Hausse"),
    ("stable", "Stable"),
    ("down", "Baisse"),
]

RISK_SELECTION = [
    ("low", "Faible"),
    ("medium", "Moyen"),
    ("high", "Eleve"),
    ("critical", "Critique"),
]


class DigiplusDashboardMetric(models.Model):
    _name = "digiplus.dashboard.metric"
    _description = "DigiPlus Dashboard Metric"
    _order = "metric_type, name"

    name = fields.Char(required=True)
    metric_type = fields.Selection(METRIC_SELECTION, string="Type", required=True, default="crm")
    value_float = fields.Float(string="Valeur float")
    value_integer = fields.Integer(string="Valeur entiere")
    currency_id = fields.Many2one("res.currency", compute="_compute_currency_id", string="Devise")
    currency_value = fields.Monetary(string="Valeur monetaire", currency_field="currency_id")
    zone = fields.Char(string="Zone")
    sector = fields.Char(string="Secteur")
    period = fields.Char(string="Periode")
    trend = fields.Selection(TREND_SELECTION, string="Tendance", default="stable")
    risk_level = fields.Selection(RISK_SELECTION, string="Risque", default="low")
    description = fields.Text(string="Description")

    def _compute_currency_id(self):
        company_currency = self.env["res.company"]._get_preferred_display_currency()
        for record in self:
            record.currency_id = company_currency

    def cron_refresh_operational_metrics(self):
        products = self.env["product.template"].search(
            [("x_rupture_risk_level", "in", ["high", "critical"])]
        )
        period = fields.Date.today().strftime("%Y-%m")
        for product in products:
            name = "Risque de rupture - %s" % product.name
            if self.search([("name", "=", name), ("period", "=", period)], limit=1):
                continue
            self.create(
                {
                    "name": name,
                    "metric_type": "stock",
                    "value_float": product.list_price,
                    "value_integer": int(product.qty_available),
                    "currency_value": product.standard_price,
                    "zone": "Operations internes",
                    "sector": product.x_solution_family or "support",
                    "period": period,
                    "trend": "down",
                    "risk_level": product.x_rupture_risk_level,
                    "description": "Mise a jour automatique des indicateurs de disponibilite.",
                }
            )
        return True
