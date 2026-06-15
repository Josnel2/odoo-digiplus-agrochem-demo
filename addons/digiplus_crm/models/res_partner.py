import re

from odoo import api, fields, models

from .selections import BUSINESS_SECTOR_SELECTION, CONTACT_LANGUAGE_SELECTION, PRIORITY_SELECTION, SERVICE_SELECTION


class ResPartner(models.Model):
    _inherit = "res.partner"

    x_partner_business_sector = fields.Selection(BUSINESS_SECTOR_SELECTION, string="Secteur d'activite")
    x_partner_priority_level = fields.Selection(PRIORITY_SELECTION, string="Priorite commerciale")
    x_preferred_service_requested = fields.Selection(SERVICE_SELECTION, string="Service d'interet")
    x_partner_account_notes = fields.Text(string="Notes commerciales")
    x_contact_language = fields.Selection(
        CONTACT_LANGUAGE_SELECTION,
        string="Langue de contact",
        help="Langue privilegiee pour les echanges commerciaux.",
    )

    @api.model
    def normalize_email(self, email):
        return (email or "").strip().lower()

    @api.model
    def normalize_phone(self, phone):
        return re.sub(r"[^0-9+]", "", (phone or "").strip())

    @api.model
    def sanitize_installed_lang(self, lang_code):
        lang_code = (lang_code or "").strip()
        if not lang_code:
            return False
        lang = self.env["res.lang"].sudo().search([("code", "=", lang_code)], limit=1)
        return lang.code or False

    @api.model
    def get_fallback_installed_lang(self, preferred_lang=None):
        preferred_lang = self.sanitize_installed_lang(preferred_lang)
        if preferred_lang:
            return preferred_lang
        en_lang = self.sanitize_installed_lang("en_US")
        if en_lang:
            return en_lang
        fallback_lang = self.env["res.lang"].sudo().search([], limit=1)
        return fallback_lang.code or False

    @api.model
    def _sanitize_partner_lang_vals(self, vals):
        if "lang" not in vals:
            return vals
        sanitized_vals = dict(vals)
        sanitized_vals["lang"] = self.sanitize_installed_lang(sanitized_vals.get("lang"))
        return sanitized_vals

    @api.model_create_multi
    def create(self, vals_list):
        sanitized_vals_list = [self._sanitize_partner_lang_vals(vals) for vals in vals_list]
        return super().create(sanitized_vals_list)

    def write(self, vals):
        return super().write(self._sanitize_partner_lang_vals(vals))

    @api.model
    def _sanitize_invalid_partner_languages(self):
        installed_langs = set(self.env["res.lang"].sudo().search([]).mapped("code"))
        if not installed_langs:
            return True
        invalid_partners = self.sudo().with_context(active_test=False).search([("lang", "!=", False)]).filtered(
            lambda partner: (partner.lang or "").strip() not in installed_langs
        )
        if invalid_partners:
            invalid_partners.write({"lang": False})
        return True
