from odoo import api, models
from odoo.exceptions import UserError


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
    def _set_company_currency_if_possible(self, company, currency):
        company.write({"currency_id": currency.id})
        return True

    @api.model
    def _normalize_company_currency_to_xaf(self):
        xaf_currency = self._get_preferred_display_currency()
        if not xaf_currency:
            return True

        companies = self.sudo().with_context(active_test=False).search([])
        normalized_companies = self.browse()
        blocked_companies = self.browse()
        for company in companies.filtered(lambda company: company.currency_id != xaf_currency):
            try:
                self._set_company_currency_if_possible(company, xaf_currency)
            except UserError:
                # Odoo blocks currency changes once journal items exist.
                # Skip those companies so upgrades and local test installs stay runnable,
                # but do not cascade XAF onto shared pricing data if the company stayed unchanged.
                blocked_companies |= company
                continue
            normalized_companies |= company

        pricelists = self.env["product.pricelist"].sudo().with_context(active_test=False).search([])
        if "company_id" in pricelists._fields:
            pricelists.filtered(
                lambda pricelist: pricelist.company_id
                and pricelist.company_id in normalized_companies
                and pricelist.currency_id != xaf_currency
            ).write({"currency_id": xaf_currency.id})
            if not blocked_companies:
                pricelists.filtered(
                    lambda pricelist: not pricelist.company_id and pricelist.currency_id != xaf_currency
                ).write({"currency_id": xaf_currency.id})
        elif not blocked_companies:
            pricelists.filtered(lambda pricelist: pricelist.currency_id != xaf_currency).write(
                {"currency_id": xaf_currency.id}
            )
        return True
