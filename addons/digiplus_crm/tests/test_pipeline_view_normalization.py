from odoo.tests.common import TransactionCase


class TestDigiplusCrmPipelineViewNormalization(TransactionCase):
    def test_pipeline_view_normalization_sanitizes_progressbar_and_updates_action(self):
        old_view = self.env["ir.ui.view"].create(
            {
                "name": "digiplus.crm.lead.kanban legacy",
                "model": "crm.lead",
                "type": "kanban",
                "arch_db": """
                    <kanban>
                        <progressbar field="activity_state" colors="{'planned': 'success'}"/>
                        <field name="name"/>
                        <templates>
                            <t t-name="card"><div><field name="name"/></div></t>
                        </templates>
                    </kanban>
                """,
            }
        )
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "Legacy pipeline",
                "res_model": "crm.lead",
                "view_mode": "kanban,list,form",
                "view_id": old_view.id,
            }
        )

        self.env["ir.ui.view"]._normalize_digiplus_crm_pipeline_views()

        target_view = self.env.ref("digiplus_crm.view_digiplus_crm_lead_kanban_v2")
        self.assertNotIn("<progressbar", old_view.arch_db)
        self.assertEqual(action.view_id, target_view)

    def test_pipeline_view_normalization_updates_legacy_search_views(self):
        legacy_search_view = self.env["ir.ui.view"].create(
            {
                "name": "digiplus.crm.lead.search legacy",
                "model": "crm.lead",
                "type": "search",
                "arch_db": """
                    <search>
                        <field name="name"/>
                        <field name="digiplus_priority_level"/>
                        <filter
                            name="legacy_priority"
                            string="Priorite legacy"
                            domain="[('digiplus_priority_level', '=', 'high')]"
                        />
                    </search>
                """,
            }
        )
        wrong_search_view = self.env["ir.ui.view"].create(
            {
                "name": "crm.lead.search wrong model",
                "model": "res.partner",
                "type": "search",
                "arch_db": """
                    <search>
                        <field name="name"/>
                    </search>
                """,
            }
        )
        legacy_action = self.env["ir.actions.act_window"].create(
            {
                "name": "Legacy pipeline search",
                "res_model": "crm.lead",
                "view_mode": "kanban,list,form",
                "search_view_id": legacy_search_view.id,
            }
        )
        wrong_action = self.env["ir.actions.act_window"].create(
            {
                "name": "Wrong pipeline search",
                "res_model": "crm.lead",
                "view_mode": "kanban,list,form",
                "search_view_id": wrong_search_view.id,
            }
        )

        self.env["ir.ui.view"]._normalize_digiplus_crm_pipeline_views()

        target_search_view = self.env.ref("digiplus_crm.view_digiplus_crm_lead_search")
        self.assertNotIn("digiplus_priority_level", legacy_search_view.arch_db)
        self.assertIn("x_priority_level", legacy_search_view.arch_db)
        self.assertEqual(legacy_action.search_view_id, target_search_view)
        self.assertEqual(wrong_action.search_view_id, target_search_view)
