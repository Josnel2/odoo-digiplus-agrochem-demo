from odoo import api, models


DIGIPLUS_UTM_SOURCE_XMLIDS = {
    "digiplus_agrochem_demo.utm_source_visit": "Atelier diagnostic",
    "digiplus_agrochem_demo.utm_source_referral": "Recommandation client",
    "digiplus_agrochem_demo.utm_source_linkedin": "LinkedIn",
    "digiplus_agrochem_demo.utm_source_event": "Webinar DigiPlus",
    "digiplus_agrochem_demo.utm_source_email": "Campagne email",
    "digiplus_agrochem_demo.utm_source_inbound": "Appel entrant",
}


class UtmSource(models.Model):
    _inherit = "utm.source"

    @api.model
    def _reassign_digiplus_utm_source_references(self, source_to_keep, source_to_replace):
        if not source_to_keep or not source_to_replace or source_to_keep == source_to_replace:
            return

        fields = self.env["ir.model.fields"].sudo().search(
            [
                ("ttype", "=", "many2one"),
                ("relation", "=", "utm.source"),
                ("store", "=", True),
            ]
        )
        for field in fields:
            try:
                model = self.env[field.model]
            except KeyError:
                continue
            if not getattr(model, "_auto", False):
                continue
            table = model._table
            self.env.cr.execute(
                f'UPDATE "{table}" SET "{field.name}" = %s WHERE "{field.name}" = %s',
                (source_to_keep.id, source_to_replace.id),
            )

    @api.model
    def _normalize_digiplus_utm_sources(self):
        Source = self.sudo().with_context(active_test=False)
        ModelData = self.env["ir.model.data"].sudo().with_context(active_test=False)

        for full_xmlid, target_name in DIGIPLUS_UTM_SOURCE_XMLIDS.items():
            module, name = full_xmlid.split(".", 1)
            bound_source = self.env.ref(full_xmlid, raise_if_not_found=False)
            target_source = Source.search([("name", "=", target_name)], order="id", limit=1)
            model_data = ModelData.search(
                [
                    ("module", "=", module),
                    ("name", "=", name),
                    ("model", "=", "utm.source"),
                ],
                limit=1,
            )

            if target_source and bound_source and target_source != bound_source:
                Source._reassign_digiplus_utm_source_references(target_source, bound_source)
                model_data.write({"res_id": target_source.id})
                if "active" in bound_source._fields:
                    bound_source.write({"active": False})
                continue

            if target_source and not bound_source:
                if model_data:
                    model_data.write({"res_id": target_source.id})
                else:
                    ModelData.create(
                        {
                            "module": module,
                            "name": name,
                            "model": "utm.source",
                            "res_id": target_source.id,
                            "noupdate": True,
                        }
                    )

        self.env.invalidate_all()
        return True
