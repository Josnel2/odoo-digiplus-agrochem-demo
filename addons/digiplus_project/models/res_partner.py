from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    digiplus_project_count = fields.Integer(string="# Projets", compute="_compute_digiplus_project_count")

    def _compute_digiplus_project_count(self):
        project_data = self.env["project.project"]._read_group(
            [("partner_id", "child_of", self.ids)],
            ["partner_id"],
            ["__count"],
        )
        counts_by_partner = {}
        for partner, count in project_data:
            current_partner = partner
            while current_partner:
                counts_by_partner[current_partner.id] = counts_by_partner.get(current_partner.id, 0) + count
                current_partner = current_partner.parent_id
        for partner in self:
            partner.digiplus_project_count = counts_by_partner.get(partner.id, 0)

    def action_view_digiplus_projects(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("project.open_view_project_all")
        action["name"] = _("%s - Projets") % self.display_name
        action["domain"] = [("partner_id", "child_of", self.id)]
        action["context"] = {"default_partner_id": self.id}
        return action
