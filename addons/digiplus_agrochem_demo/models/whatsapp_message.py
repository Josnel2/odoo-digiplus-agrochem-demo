from odoo import fields, models


MESSAGE_TYPE_SELECTION = [
    ("intro", "Introduction"),
    ("followup", "Relance"),
    ("proposal", "Proposition"),
    ("reminder", "Rappel"),
]

STATUS_SELECTION = [
    ("draft", "Brouillon"),
    ("ready", "Pret"),
    ("sent", "Envoye"),
    ("delivered", "Livre"),
    ("failed", "Echec"),
    ("replied", "Repondu"),
]


class DigiplusWhatsappMessage(models.Model):
    _name = "digiplus.whatsapp.message"
    _description = "DigiPlus WhatsApp Message"
    _order = "create_date desc"

    name = fields.Char(required=True)
    partner_id = fields.Many2one("res.partner", string="Contact")
    crm_lead_id = fields.Many2one("crm.lead", string="Opportunite")
    phone_number = fields.Char(string="Numero")
    message_type = fields.Selection(MESSAGE_TYPE_SELECTION, string="Type", default="followup", required=True)
    message_body = fields.Text(string="Message")
    status = fields.Selection(STATUS_SELECTION, string="Statut", default="draft", required=True)
    sent_date = fields.Datetime(string="Date d'envoi")
    response_date = fields.Datetime(string="Date de reponse")
    response_summary = fields.Text(string="Resume de reponse")
    api_reference = fields.Char(string="Reference API")

    def action_mark_ready(self):
        self.write({"status": "ready"})
        return True

    def action_send_message(self):
        now = fields.Datetime.now()
        for message in self:
            message.write(
                {
                    "status": "sent",
                    "sent_date": now,
                    "api_reference": message.api_reference or ("WA-%s" % message.id),
                }
            )
        return True

    def action_mark_replied(self):
        self.write({"status": "replied", "response_date": fields.Datetime.now()})
        return True
