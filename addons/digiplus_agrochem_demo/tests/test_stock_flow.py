from odoo.tests.common import TransactionCase


class TestStockFlow(TransactionCase):
    def test_dashboard_metric_created_for_high_risk_product(self):
        template = self.env["product.template"].create(
            {
                "name": "Produit Rupture Test",
                "type": "consu",
                "list_price": 2500.0,
                "x_solution_family": "stock",
                "x_rupture_risk_level": "high",
            }
        )
        metric = self.env["digiplus.dashboard.metric"].search(
            [("name", "=", "Risque de rupture - %s" % template.name)],
            limit=1,
        )
        self.assertTrue(metric)
