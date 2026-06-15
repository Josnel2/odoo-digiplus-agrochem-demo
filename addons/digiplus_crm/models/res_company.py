from odoo import api, models


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def _normalize_company_branding(self):
        target_name = "DigiPlus Consulting"
        demo_names = {
            "my company",
            "my company (san francisco)",
            "yourcompany",
            "your company",
        }

        main_company = self.env.ref("base.main_company", raise_if_not_found=False)
        main_partner = self.env.ref("base.main_partner", raise_if_not_found=False)

        companies = self.sudo().with_context(active_test=False).search([])
        companies_to_rename = companies.filtered(
            lambda company: company == main_company or (company.name or "").strip().lower() in demo_names
        )
        if companies_to_rename:
            companies_to_rename.write({"name": target_name})

        partners_to_rename = self.env["res.partner"].sudo().browse()
        if main_partner:
            partners_to_rename |= main_partner
        partners_to_rename |= companies_to_rename.mapped("partner_id").filtered(
            lambda partner: (partner.name or "").strip().lower() in demo_names or partner == main_partner
        )
        if partners_to_rename:
            partners_to_rename.write({"name": target_name})
        return True

    @api.model
    def _get_preferred_display_currency(self):
        xaf_currency = self.env["res.currency"].sudo().with_context(active_test=False).search(
            [("name", "=", "XAF")],
            limit=1,
        )
        if xaf_currency:
            return xaf_currency
        return self.env.company.currency_id

    @api.model
    def _normalize_company_currency_to_xaf(self):
        xaf_currency = self._get_preferred_display_currency()
        if not xaf_currency:
            return True

        companies = self.sudo().with_context(active_test=False).search([])
        companies.filtered(lambda company: company.currency_id != xaf_currency).write({"currency_id": xaf_currency.id})

        pricelists = self.env["product.pricelist"].sudo().with_context(active_test=False).search([])
        pricelists.filtered(lambda pricelist: pricelist.currency_id != xaf_currency).write({"currency_id": xaf_currency.id})
        return True
