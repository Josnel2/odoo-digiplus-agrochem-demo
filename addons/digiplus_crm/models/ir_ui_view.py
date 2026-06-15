from lxml import etree

from odoo import api, models


class IrUiView(models.Model):
    _inherit = "ir.ui.view"

    @api.model
    def _normalize_digiplus_crm_pipeline_views(self):
        pipeline_views = self.sudo().with_context(active_test=False).search(
            [
                ("model", "=", "crm.lead"),
                ("name", "ilike", "digiplus.crm.lead.kanban"),
            ]
        )
        sanitized_views = self.browse()
        for view in pipeline_views:
            if "<progressbar" not in (view.arch_db or ""):
                continue
            root = etree.fromstring(view.arch_db.encode("utf-8"))
            progressbars = root.xpath("//progressbar")
            if not progressbars:
                continue
            for node in progressbars:
                node.getparent().remove(node)
            view.write({"arch_db": etree.tostring(root, encoding="unicode")})
            sanitized_views |= view

        target_view = self.env.ref("digiplus_crm.view_digiplus_crm_lead_kanban_v2", raise_if_not_found=False)
        if not target_view:
            return True

        action_model = self.env["ir.actions.act_window"].sudo().with_context(active_test=False)
        actions = action_model.search(
            [
                ("res_model", "=", "crm.lead"),
                ("view_id", "in", (pipeline_views | sanitized_views).ids),
            ]
        )
        for xmlid in (
            "digiplus_crm.action_digiplus_crm_pipeline",
            "digiplus_agrochem_demo.action_digiplus_crm_pipeline",
            "digiplus_agrochem_demo.action_digiplus_agrochem_opps",
        ):
            action = self.env.ref(xmlid, raise_if_not_found=False)
            if action:
                actions |= action
        if actions:
            actions.write({"view_id": target_view.id})
        return True
