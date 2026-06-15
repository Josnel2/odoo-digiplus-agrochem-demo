from odoo import api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _sanitize_user_lang_vals(self, vals):
        if "lang" not in vals:
            return vals
        sanitized_vals = dict(vals)
        sanitized_vals["lang"] = self.env["res.partner"].get_fallback_installed_lang(
            preferred_lang=sanitized_vals.get("lang")
        )
        return sanitized_vals

    @api.model_create_multi
    def create(self, vals_list):
        sanitized_vals_list = [self._sanitize_user_lang_vals(vals) for vals in vals_list]
        return super().create(sanitized_vals_list)

    def write(self, vals):
        return super().write(self._sanitize_user_lang_vals(vals))

    @api.model
    def _sanitize_invalid_user_languages(self):
        installed_langs = set(self.env["res.lang"].sudo().search([]).mapped("code"))
        if not installed_langs:
            return True
        fallback_lang = self.env["res.partner"].get_fallback_installed_lang()
        invalid_users = self.sudo().with_context(active_test=False).search([("lang", "!=", False)]).filtered(
            lambda user: (user.lang or "").strip() not in installed_langs
        )
        if invalid_users and fallback_lang:
            invalid_users.write({"lang": fallback_lang})
        return True
