from odoo.tests.common import TransactionCase


class TestDigiplusUtmSourceNormalization(TransactionCase):
    def test_normalization_rebinds_xmlid_to_existing_source(self):
        canonical_source = self.env["utm.source"].search([("name", "=", "LinkedIn")], order="id", limit=1)
        if not canonical_source:
            canonical_source = self.env["utm.source"].create({"name": "LinkedIn"})

        legacy_source = self.env["utm.source"].create({"name": "Reseau LinkedIn"})
        lead = self.env["crm.lead"].create(
            {
                "name": "Lead Source Legacy",
                "type": "opportunity",
                "phone": "+237690000001",
                "user_id": self.env.user.id,
                "source_id": legacy_source.id,
            }
        )
        model_data = self.env["ir.model.data"].search(
            [
                ("module", "=", "digiplus_agrochem_demo"),
                ("name", "=", "utm_source_linkedin"),
                ("model", "=", "utm.source"),
            ],
            limit=1,
        )
        if model_data:
            model_data.write({"res_id": legacy_source.id})
        else:
            self.env["ir.model.data"].create(
                {
                    "module": "digiplus_agrochem_demo",
                    "name": "utm_source_linkedin",
                    "model": "utm.source",
                    "res_id": legacy_source.id,
                    "noupdate": True,
                }
            )

        self.env["utm.source"]._normalize_digiplus_utm_sources()

        lead.invalidate_recordset(["source_id"])
        self.assertEqual(lead.source_id, canonical_source)
        self.assertEqual(
            self.env.ref("digiplus_agrochem_demo.utm_source_linkedin", raise_if_not_found=False),
            canonical_source,
        )
