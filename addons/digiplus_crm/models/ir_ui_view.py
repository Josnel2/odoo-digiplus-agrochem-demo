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

        target_search_view = self.env.ref("digiplus_crm.view_digiplus_crm_lead_search", raise_if_not_found=False)
        legacy_search_views = self.sudo().with_context(active_test=False).search(
            [
                ("model", "=", "crm.lead"),
                ("type", "=", "search"),
                ("arch_db", "ilike", "digiplus_priority_level"),
            ]
        )
        for view in legacy_search_views:
            view.write({"arch_db": view.arch_db.replace("digiplus_priority_level", "x_priority_level")})

        if target_search_view:
            search_actions = action_model.search([("res_model", "=", "crm.lead")])
            stale_search_actions = search_actions.filtered(
                lambda action: action.search_view_id
                and (
                    action.search_view_id.model != "crm.lead"
                    or "digiplus_priority_level" in (action.search_view_id.arch_db or "")
                )
            )
            for xmlid in (
                "digiplus_crm.action_digiplus_crm_pipeline",
                "digiplus_agrochem_demo.action_digiplus_crm_pipeline",
                "digiplus_agrochem_demo.action_digiplus_agrochem_opps",
            ):
                action = self.env.ref(xmlid, raise_if_not_found=False)
                if action:
                    stale_search_actions |= action
            if stale_search_actions:
                stale_search_actions.write({"search_view_id": target_search_view.id})
        return True
