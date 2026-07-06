import unicodedata

from odoo import api, models


DIGIPLUS_STAGE_PIPELINE = {
    "digiplus_crm.stage_prospect": {
        "name": "Prospect",
        "sequence": 10,
        "fold": False,
        "aliases": ["new", "nouveau prospect", "prospect"],
    },
    "digiplus_crm.stage_qualified": {
        "name": "Qualifie",
        "sequence": 20,
        "fold": False,
        "aliases": ["qualified", "qualifie", "besoin qualifie", "atelier de cadrage", "offre a preparer"],
    },
    "digiplus_crm.stage_proposal_sent": {
        "name": "Proposition envoyee",
        "sequence": 30,
        "fold": False,
        "aliases": ["proposition", "proposition envoyee"],
    },
    "digiplus_crm.stage_negotiation": {
        "name": "Negociation",
        "sequence": 40,
        "fold": False,
        "aliases": ["negotiation", "negociation", "relance commerciale"],
    },
    "digiplus_crm.stage_won": {
        "name": "Gagne",
        "sequence": 50,
        "fold": True,
        "aliases": ["won", "gagne", "bon de commande recu"],
    },
    "digiplus_crm.stage_lost": {
        "name": "Perdu",
        "sequence": 60,
        "fold": True,
        "aliases": ["lost", "perdu"],
    },
}


class CrmStage(models.Model):
    _inherit = "crm.stage"

    @api.model
    def _normalize_digiplus_stage_key(self, label):
        normalized = unicodedata.normalize("NFKD", label or "")
        ascii_label = normalized.encode("ascii", "ignore").decode("ascii")
        return " ".join(ascii_label.lower().split())

    @api.model
    def _archive_digiplus_stage(self, stage):
        vals = {"fold": True}
        if "active" in stage._fields:
            vals["active"] = False
        stage.write(vals)

    @api.model
    def _get_digiplus_stage_alias_map(self):
        alias_map = {}
        for xmlid, definition in DIGIPLUS_STAGE_PIPELINE.items():
            labels = definition["aliases"] + [definition["name"]]
            for label in labels:
                alias_map[self._normalize_digiplus_stage_key(label)] = xmlid
        return alias_map

    @api.model
    def _get_or_create_digiplus_target_stage(self, xmlid, definition):
        stage = self.env.ref(xmlid, raise_if_not_found=False)
        if not stage:
            stage = self.search([("name", "=", definition["name"])], limit=1)
        vals = {
            "name": definition["name"],
            "sequence": definition["sequence"],
            "fold": definition["fold"],
        }
        if stage:
            stage.write(vals)
            return stage
        return self.create(vals)

    @api.model
    def _normalize_digiplus_crm_stages(self):
        Stage = self.sudo().with_context(active_test=False)
        Lead = self.env["crm.lead"].sudo().with_context(
            active_test=False,
            install_mode=True,
            skip_digiplus_stage_validation=True,
        )
        alias_map = self._get_digiplus_stage_alias_map()
        target_stages = {}
        for xmlid, definition in DIGIPLUS_STAGE_PIPELINE.items():
            target_stages[xmlid] = Stage._get_or_create_digiplus_target_stage(xmlid, definition)

        target_ids = {stage.id for stage in target_stages.values()}
        target_names = {definition["name"] for definition in DIGIPLUS_STAGE_PIPELINE.values()}

        for stage in Stage.search([]):
            normalized_key = self._normalize_digiplus_stage_key(stage.name)
            target_xmlid = alias_map.get(normalized_key)
            if not target_xmlid:
                continue
            target_stage = target_stages[target_xmlid]
            if stage.id == target_stage.id:
                continue
            leads = Lead.search([("stage_id", "=", stage.id)])
            if leads:
                vals = {"stage_id": target_stage.id}
                if target_xmlid == "digiplus_crm.stage_lost":
                    loss_reason_leads = leads.filtered(lambda record: not record.x_loss_reason)
                    for lead in loss_reason_leads:
                        lead.write({"stage_id": target_stage.id, "x_loss_reason": "Perte normalisee du pipeline CRM."})
                    leads -= loss_reason_leads
                if leads:
                    leads.write(vals)
            Stage._archive_digiplus_stage(stage)

        for stage in Stage.search([("id", "not in", list(target_ids))]):
            if stage.name in target_names:
                continue
            if Lead.search_count([("stage_id", "=", stage.id)]):
                continue
            Stage._archive_digiplus_stage(stage)
        return True
