from odoo.tests.common import TransactionCase


class TestDigiplusCrmStageNormalization(TransactionCase):
    def test_normalization_merges_duplicate_pipeline_stages(self):
        legacy_stage = self.env["crm.stage"].create({"name": "Atelier de cadrage", "sequence": 999})
        lead = self.env["crm.lead"].create(
            {
                "name": "Legacy Pipeline Lead",
                "type": "opportunity",
                "phone": "+237690000000",
                "user_id": self.env.user.id,
                "stage_id": legacy_stage.id,
            }
        )

        self.env["crm.stage"]._normalize_digiplus_crm_stages()

        lead.invalidate_recordset(["stage_id"])
        stage_fields = ["fold"]
        if "active" in legacy_stage._fields:
            stage_fields.append("active")
        legacy_stage.invalidate_recordset(stage_fields)
        target_stage = self.env.ref("digiplus_crm.stage_qualified")

        self.assertEqual(lead.stage_id, target_stage)
        self.assertTrue(legacy_stage.fold)
        if "active" in legacy_stage._fields:
            self.assertFalse(legacy_stage.active)
