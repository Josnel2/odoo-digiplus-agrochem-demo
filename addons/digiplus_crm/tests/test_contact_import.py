import base64

from odoo.tests.common import TransactionCase


class TestDigiplusCrmContactImport(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env["res.partner"].create(
            {
                "name": "Vision Retail Group",
                "company_type": "company",
                "email": "contact@visionretail.example",
                "phone": "+237699000111",
            }
        )

    def test_parse_and_apply_import(self):
        csv_payload = "\n".join(
            [
                "company_name,contact_name,email,phone,mobile,job_title,website,sector,service_requested,source,salesperson,priority,notes,language",
                "Vision Retail Group,Jean Dupont,contact@visionretail.example,+237699000111,,Directeur,https://visionretail.example,Distribution,CRM,Recommandation,%s,Haute,Compte existant,fr_FR"
                % self.env.user.name,
                "Nova Manufacturing,Emma Nde,emma@nova.example,+237677888999,,DG,https://nova.example,Industrie,ERP / Odoo,Evenement,%s,Critique,Nouveau compte,en_US"
                % self.env.user.name,
            ]
        )
        wizard = self.env["digiplus.crm.contact.import.wizard"].create(
            {
                "filename": "contacts.csv",
                "data_file": base64.b64encode(csv_payload.encode("utf-8")),
            }
        )

        wizard.action_parse_file()
        self.assertEqual(wizard.line_count, 2)
        duplicate_line = wizard.line_ids.filtered(lambda line: line.company_name == "Vision Retail Group")
        create_line = wizard.line_ids.filtered(lambda line: line.company_name == "Nova Manufacturing")
        self.assertEqual(duplicate_line.action_recommended, "link")
        self.assertEqual(create_line.action_recommended, "create")

        wizard.action_apply_import()
        created_partner = self.env["res.partner"].search([("name", "=", "Nova Manufacturing")], limit=1)
        created_lead = self.env["crm.lead"].search([("partner_id", "=", created_partner.id)], limit=1)
        self.assertTrue(created_partner)
        self.assertTrue(created_lead)
        self.assertEqual(created_lead.x_service_requested, "erp_odoo")
