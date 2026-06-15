from odoo import http
from odoo.http import request


class DigiplusDashboardApiController(http.Controller):
    @http.route("/digiplus/dashboard/metrics", type="json", auth="user", methods=["GET"], csrf=False)
    def dashboard_metrics(self, metric_type=None, limit=20, **kwargs):
        domain = []
        if metric_type:
            domain.append(("metric_type", "=", metric_type))
        metrics = request.env["digiplus.dashboard.metric"].sudo().search(domain, limit=int(limit))
        return {
            "count": len(metrics),
            "items": [
                {
                    "name": metric.name,
                    "metric_type": metric.metric_type,
                    "value_float": metric.value_float,
                    "value_integer": metric.value_integer,
                    "currency_value": metric.currency_value,
                    "zone": metric.zone,
                    "sector": metric.sector,
                    "period": metric.period,
                    "trend": metric.trend,
                    "risk_level": metric.risk_level,
                }
                for metric in metrics
            ],
        }
