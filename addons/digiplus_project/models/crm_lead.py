from odoo import _, api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    project_ids = fields.One2many("project.project", "origin_opportunity_id", string="Projets")
    digiplus_project_count = fields.Integer(string="# Projets", compute="_compute_digiplus_project_count")

    def _compute_digiplus_project_count(self):
        for lead in self:
            lead.digiplus_project_count = len(lead.project_ids)

    def _prepare_digiplus_project_creation_vals(self):
        self.ensure_one()
        if hasattr(self, "_ensure_partner_for_conversion"):
            self._ensure_partner_for_conversion()
        if hasattr(self, "prepare_project_vals"):
            values = dict(self.prepare_project_vals())
        else:
            values = {
                "name": self.name,
                "partner_id": self.partner_id.id,
                "user_id": self.user_id.id or self.env.user.id,
            }
        values.setdefault("name", self.name)
        values.setdefault("partner_id", self.partner_id.id if self.partner_id else False)
        values.setdefault("user_id", self.user_id.id or self.env.user.id)
        values.setdefault("origin_opportunity_id", self.id)
        values.setdefault("allow_timesheets", True)
        values.setdefault("allow_billable", True)
        values.setdefault("digiplus_is_template", False)
        return values

    def action_create_digiplus_project(self):
        self.ensure_one()
        existing_project = self.env["project.project"].search(
            [("origin_opportunity_id", "=", self.id)],
            limit=1,
        )
        if existing_project:
            return {
                "type": "ir.actions.act_window",
                "name": _("Projet lie"),
                "res_model": "project.project",
                "view_mode": "form",
                "res_id": existing_project.id,
                "views": [(self.env.ref("project.edit_project").id, "form")],
            }
        project = self.env["project.project"].create(self._prepare_digiplus_project_creation_vals())
        return {
            "type": "ir.actions.act_window",
            "name": _("Projet cree"),
            "res_model": "project.project",
            "view_mode": "form",
            "res_id": project.id,
            "views": [(self.env.ref("project.edit_project").id, "form")],
        }

    def action_view_digiplus_projects(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("project.open_view_project_all")
        action["name"] = _("%s - Projets") % self.display_name
        action["domain"] = [("origin_opportunity_id", "=", self.id)]
        action["context"] = {
            "default_origin_opportunity_id": self.id,
            "default_partner_id": self.partner_id.id if self.partner_id else False,
            "default_user_id": self.user_id.id or self.env.user.id,
        }
        return action
