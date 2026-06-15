from odoo import api, fields, models


FAMILY_SELECTION = [
    ("crm", "CRM"),
    ("erp", "ERP / Odoo"),
    ("web", "Developpement web"),
    ("mobile", "Developpement mobile"),
    ("automation", "Automatisation"),
    ("bi", "Business Intelligence"),
    ("training", "Formation"),
    ("support", "Maintenance / support"),
    ("marketing", "Marketing"),
    ("consulting", "Conseil"),
    ("integration", "Integration"),
]

ROTATION_SELECTION = [
    ("fast", "Forte rotation"),
    ("medium", "Rotation moyenne"),
    ("slow", "Faible rotation"),
    ("dormant", "Dormant"),
]

RISK_SELECTION = [
    ("low", "Faible"),
    ("medium", "Moyen"),
    ("high", "Eleve"),
    ("critical", "Critique"),
]


class ProductTemplate(models.Model):
    _inherit = "product.template"

    x_solution_family = fields.Selection(FAMILY_SELECTION, string="Famille de solution")
    x_demo_axis = fields.Char(string="Offre / axe")
    x_business_value = fields.Text(string="Valeur business")
    x_target_module = fields.Char(string="Module cible")
    x_is_demo_service = fields.Boolean(string="Offre DigiPlus")
    x_agrochem_equivalent = fields.Char(string="Offre associee")
    x_stock_rotation_category = fields.Selection(ROTATION_SELECTION, string="Categorie de rotation")
    x_rupture_risk_level = fields.Selection(RISK_SELECTION, string="Risque de rupture", default="low")

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        if not self.env.context.get("install_mode"):
            products._ensure_rupture_metrics()
        return products

    def write(self, vals):
        result = super().write(vals)
        if not self.env.context.get("install_mode"):
            self._ensure_rupture_metrics()
        return result

    def _ensure_rupture_metrics(self):
        metric_model = self.env["digiplus.dashboard.metric"].sudo()
        period = fields.Date.today().strftime("%Y-%m")
        for product in self.filtered(lambda p: p.x_rupture_risk_level in ("high", "critical")):
            name = "Risque de rupture - %s" % product.name
            existing = metric_model.search([("name", "=", name), ("period", "=", period)], limit=1)
            if existing:
                continue
            metric_model.create(
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
                    "description": "Produit ou licence a surveiller pour la continuite des services.",
                }
            )

    def action_create_rupture_metric(self):
        self._ensure_rupture_metrics()
        return True
