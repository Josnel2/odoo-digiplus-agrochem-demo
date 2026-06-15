from odoo import http
from odoo.http import request


class DigiplusWhatsappController(http.Controller):
    @http.route("/digiplus/whatsapp/send", type="json", auth="user", methods=["POST"], csrf=False)
    def send_whatsapp(self, message_id=None, lead_id=None, partner_id=None, body=None, **kwargs):
        message_model = request.env["digiplus.whatsapp.message"].sudo()
        if message_id:
            message = message_model.browse(int(message_id))
        else:
            values = {
                "name": kwargs.get("name") or "Message WhatsApp DigiPlus",
                "partner_id": int(partner_id) if partner_id else False,
                "crm_lead_id": int(lead_id) if lead_id else False,
                "phone_number": kwargs.get("phone_number"),
                "message_type": kwargs.get("message_type", "followup"),
                "message_body": body or kwargs.get("message_body") or "Message de suivi DigiPlus.",
                "status": "ready",
            }
            message = message_model.create(values)
        message.action_send_message()
        return {
            "status": "ok",
            "message_id": message.id,
            "api_reference": message.api_reference,
            "message_state": message.status,
        }
