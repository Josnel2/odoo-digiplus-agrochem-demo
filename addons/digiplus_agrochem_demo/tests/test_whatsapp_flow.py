from odoo.tests.common import TransactionCase


class TestWhatsappFlow(TransactionCase):
    def test_create_and_send_whatsapp_message(self):
        partner = self.env["res.partner"].create({"name": "Partner WhatsApp", "mobile": "+237699000999"})
        lead = self.env["crm.lead"].create({"name": "Lead WhatsApp", "type": "opportunity", "partner_id": partner.id})
        message = self.env["digiplus.whatsapp.message"].create(
            {
                "name": "Message Test",
                "partner_id": partner.id,
                "crm_lead_id": lead.id,
                "phone_number": partner.mobile,
                "message_body": "Bonjour depuis le test.",
            }
        )
        message.action_send_message()
        self.assertEqual(message.status, "sent")
        self.assertTrue(message.api_reference)
