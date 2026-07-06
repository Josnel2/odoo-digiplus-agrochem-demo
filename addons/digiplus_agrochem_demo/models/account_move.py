from odoo import fields, models


EXPORT_SELECTION = [
    ("not_concerned", "Non concerne par export externe"),
    ("not_exported", "Non exporte"),
    ("ready", "Pret pour export externe"),
    ("exported", "Exporte"),
    ("error", "Erreur export"),
]


class AccountMove(models.Model):
    _inherit = "account.move"

    x_sage_saari_export_status = fields.Selection(
        EXPORT_SELECTION, string="Statut export externe", default="not_concerned"
    )
    x_sage_saari_reference = fields.Char(string="Reference export externe")
    x_integration_comment = fields.Text(string="Commentaire export / integration")

    def action_mark_ready_for_export(self):
        self.write({"x_sage_saari_export_status": "ready"})
        return True

    def action_mark_ready_for_sage(self):
        return self.action_mark_ready_for_export()
