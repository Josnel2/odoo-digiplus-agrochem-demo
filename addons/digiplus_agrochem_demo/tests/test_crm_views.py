from odoo.tests.common import TransactionCase


class TestCrmViews(TransactionCase):
    def test_pipeline_actions_use_digiplus_crm_views(self):
        pipeline_action = self.env.ref("digiplus_agrochem_demo.action_digiplus_crm_pipeline")
        priority_action = self.env.ref("digiplus_agrochem_demo.action_digiplus_agrochem_opps")
        kanban_view = self.env.ref("digiplus_crm.view_digiplus_crm_lead_kanban_v2")
        search_view = self.env.ref("digiplus_crm.view_digiplus_crm_lead_search")

        self.assertEqual(pipeline_action.view_id, kanban_view)
        self.assertEqual(priority_action.view_id, kanban_view)
        self.assertEqual(pipeline_action.search_view_id, search_view)
        self.assertEqual(priority_action.search_view_id, search_view)

    def test_crm_root_menu_opens_pipeline(self):
        root_menu = self.env.ref("digiplus_crm.menu_digiplus_crm_root")
        pipeline_action = self.env.ref("digiplus_crm.action_digiplus_crm_pipeline")

        self.assertEqual(root_menu.action, pipeline_action)
