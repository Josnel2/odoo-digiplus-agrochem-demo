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
