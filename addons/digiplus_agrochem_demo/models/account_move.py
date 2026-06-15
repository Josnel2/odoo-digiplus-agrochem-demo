from odoo import fields, models


EXPORT_SELECTION = [
    ("not_exported", "Non exporte vers Sage"),
    ("ready", "Pret pour export Sage"),
    ("exported", "Exporte vers Sage"),
    ("error", "Erreur export"),
]


class AccountMove(models.Model):
    _inherit = "account.move"

    x_sage_saari_export_status = fields.Selection(
        EXPORT_SELECTION, string="Statut export Sage", default="not_exported"
    )
    x_sage_saari_reference = fields.Char(string="Reference Sage Saari")
    x_integration_comment = fields.Text(string="Commentaire integration")

    def action_mark_ready_for_sage(self):
        self.write({"x_sage_saari_export_status": "ready"})
        return True
