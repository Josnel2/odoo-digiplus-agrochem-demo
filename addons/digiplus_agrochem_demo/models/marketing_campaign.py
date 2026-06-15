from odoo import fields, models


STATE_SELECTION = [
    ("draft", "Brouillon"),
    ("ready", "Pret"),
    ("active", "Actif"),
    ("done", "Cloture"),
]


class MarketingCampaign(models.Model):
    _name = "digiplus.marketing.campaign"
    _description = "DigiPlus Marketing Campaign"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    state = fields.Selection(STATE_SELECTION, default="draft", required=True)
    model_id = fields.Many2one("ir.model", string="Modele cible", required=True, ondelete="cascade")
    domain = fields.Char(string="Domaine cible")
    mailing_list_id = fields.Many2one("mailing.list", string="Liste de diffusion")
    template_id = fields.Many2one("mail.template", string="Modele d'email")
    x_target_sector = fields.Char(string="Secteur cible")
    x_campaign_axis = fields.Char(string="Axe de campagne")
    x_expected_roi = fields.Float(string="ROI attendu")
    x_demo_projection = fields.Text(string="Orientation campagne")

    def action_mark_ready(self):
        self.write({"state": "ready"})
        return True

    def action_activate(self):
        self.write({"state": "active"})
        return True
