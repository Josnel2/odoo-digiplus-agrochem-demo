from odoo.tests.common import TransactionCase


class TestDigiplusCrmLanguageSanitization(TransactionCase):
    def test_cleanup_replaces_invalid_user_language(self):
        user = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Invalid Lang User",
                "login": "invalid-lang-user",
                "email": "invalid-lang-user@example.com",
                "lang": "en_US",
            }
        )
        self.env.cr.execute("UPDATE res_partner SET lang = %s WHERE id = %s", ("zz_ZZ", user.partner_id.id))
        self.env["res.partner"].invalidate_model(["lang"])
        user.invalidate_recordset(["lang"])

        self.env["res.users"]._sanitize_invalid_user_languages()

        user.invalidate_recordset(["lang"])
        self.assertEqual(user.lang, self.env["res.partner"].get_fallback_installed_lang())

    def test_cleanup_clears_invalid_partner_language(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Invalid Lang Partner",
                "company_type": "company",
                "lang": "en_US",
            }
        )
        self.env.cr.execute("UPDATE res_partner SET lang = %s WHERE id = %s", ("zz_ZZ", partner.id))
        self.env["res.partner"].invalidate_model(["lang"])

        self.env["res.partner"]._sanitize_invalid_partner_languages()

        partner.invalidate_recordset(["lang"])
        self.assertFalse(partner.lang)
