from datetime import date, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .selections import (
    BUSINESS_SECTOR_SELECTION,
    CONTACT_LANGUAGE_SELECTION,
    NEED_TYPE_SELECTION,
    PRIORITY_SELECTION,
    SERVICE_SELECTION,
    STAGE_PROBABILITY_BY_XMLID,
)


class CrmLead(models.Model):
    _inherit = "crm.lead"

    x_service_requested = fields.Selection(SERVICE_SELECTION, string="Service demande")
    x_business_sector = fields.Selection(BUSINESS_SECTOR_SELECTION, string="Secteur d'activite")
    x_priority_level = fields.Selection(PRIORITY_SELECTION, string="Niveau de priorite", default="medium")
    digiplus_priority_level = fields.Selection(
        PRIORITY_SELECTION,
        string="Niveau de priorite DigiPlus",
        related="x_priority_level",
        readonly=False,
        store=True,
    )
    x_next_action_date = fields.Date(
        string="Date de prochaine action",
        compute="_compute_next_action_data",
        store=True,
    )
    x_missing_next_action = fields.Boolean(
        string="Sans prochaine action",
        compute="_compute_next_action_data",
        store=True,
    )
    x_is_stage_proposal_sent = fields.Boolean(
        string="Etape Proposition envoyee",
        compute="_compute_stage_flags",
        store=True,
    )
    x_is_stage_negotiation = fields.Boolean(
        string="Etape Negociation",
        compute="_compute_stage_flags",
        store=True,
    )
    x_is_stage_won = fields.Boolean(
        string="Etape Gagne",
        compute="_compute_stage_flags",
        store=True,
    )
    x_is_stage_lost = fields.Boolean(
        string="Etape Perdu",
        compute="_compute_stage_flags",
        store=True,
    )
    x_strategic_comment = fields.Text(string="Commentaire strategique")
    x_contact_language = fields.Selection(
        CONTACT_LANGUAGE_SELECTION,
        string="Langue du contact",
        default="fr_FR",
    )
    x_need_type = fields.Selection(NEED_TYPE_SELECTION, string="Type de besoin")
    x_loss_reason = fields.Text(string="Motif de perte")

    @api.depends("activity_date_deadline", "stage_id")
    def _compute_next_action_data(self):
        for lead in self:
            lead.x_next_action_date = lead.activity_date_deadline
            lead.x_missing_next_action = bool(not lead._is_closed_pipeline_stage() and not lead.activity_date_deadline)

    @api.depends("stage_id")
    def _compute_stage_flags(self):
        stage_proposal = self._get_stage_ref("digiplus_crm.stage_proposal_sent")
        stage_negotiation = self._get_stage_ref("digiplus_crm.stage_negotiation")
        stage_won = self._get_stage_ref("digiplus_crm.stage_won")
        stage_lost = self._get_stage_ref("digiplus_crm.stage_lost")
        proposal_id = stage_proposal.id if stage_proposal else False
        negotiation_id = stage_negotiation.id if stage_negotiation else False
        won_id = stage_won.id if stage_won else False
        lost_id = stage_lost.id if stage_lost else False
        for lead in self:
            lead.x_is_stage_proposal_sent = lead.stage_id.id == proposal_id
            lead.x_is_stage_negotiation = lead.stage_id.id == negotiation_id
            lead.x_is_stage_won = lead.stage_id.id == won_id
            lead.x_is_stage_lost = lead.stage_id.id == lost_id

    def _get_stage_probability_map(self):
        stage_map = {}
        for xmlid, probability in STAGE_PROBABILITY_BY_XMLID.items():
            stage = self.env.ref(xmlid, raise_if_not_found=False)
            if stage:
                stage_map[stage.id] = probability
        return stage_map

    def _get_stage_ref(self, xmlid):
        return self.env.ref(xmlid, raise_if_not_found=False)

    def _is_closed_pipeline_stage(self):
        self.ensure_one()
        won_stage = self._get_stage_ref("digiplus_crm.stage_won")
        lost_stage = self._get_stage_ref("digiplus_crm.stage_lost")
        closed_stage_ids = [stage.id for stage in (won_stage, lost_stage) if stage]
        return self.stage_id.id in closed_stage_ids

    def _validate_stage_requirements(self):
        if self.env.context.get("skip_digiplus_stage_validation"):
            return
        stage_qualified = self._get_stage_ref("digiplus_crm.stage_qualified")
        stage_proposal = self._get_stage_ref("digiplus_crm.stage_proposal_sent")
        stage_negotiation = self._get_stage_ref("digiplus_crm.stage_negotiation")
        stage_won = self._get_stage_ref("digiplus_crm.stage_won")
        stage_lost = self._get_stage_ref("digiplus_crm.stage_lost")
        proposal_negotiation_ids = [stage.id for stage in (stage_proposal, stage_negotiation) if stage]

        for lead in self.filtered(lambda l: l.type == "opportunity" and l.stage_id):
            if stage_qualified and lead.stage_id == stage_qualified:
                missing = []
                if not lead.x_priority_level:
                    missing.append(_("priorite"))
                if not (lead.email_from or lead.phone):
                    missing.append(_("email ou telephone"))
                if missing:
                    raise ValidationError(_("L'etape Qualifie exige : %s.") % ", ".join(missing))

            if lead.stage_id.id in proposal_negotiation_ids:
                missing = []
                if not lead.expected_revenue:
                    missing.append(_("revenu attendu"))
                if not lead.activity_date_deadline:
                    missing.append(_("prochaine action"))
                if missing:
                    raise ValidationError(_("Cette etape exige : %s.") % ", ".join(missing))

            if stage_won and lead.stage_id == stage_won:
                missing = []
                if not (lead.partner_id or lead.partner_name):
                    missing.append(_("client ou entreprise"))
                if not lead.user_id:
                    missing.append(_("commercial responsable"))
                if not lead.expected_revenue:
                    missing.append(_("revenu attendu"))
                if missing:
                    raise ValidationError(_("L'etape Gagne exige : %s.") % ", ".join(missing))

    def _update_probability_from_stage(self, vals):
        if "stage_id" not in vals or "probability" in vals:
            return vals
        probability_map = self._get_stage_probability_map()
        stage_probability = probability_map.get(vals["stage_id"])
        if stage_probability is None:
            return vals
        updated_vals = dict(vals)
        updated_vals["probability"] = stage_probability
        return updated_vals

    def _match_partner_from_lead(self):
        self.ensure_one()
        Partner = self.env["res.partner"]
        normalized_email = Partner.normalize_email(self.email_from)
        normalized_phone = Partner.normalize_phone(self.phone)
        domain = []
        if normalized_email:
            domain = [("email", "!=", False)]
            partners = Partner.search(domain)
            for partner in partners:
                if Partner.normalize_email(partner.email) == normalized_email:
                    return partner
        candidates = Partner.search(
            [
                ("name", "ilike", self.partner_name or self.contact_name or self.name),
            ],
            limit=10,
        )
        for partner in candidates:
            if normalized_phone and Partner.normalize_phone(partner.phone) == normalized_phone:
                return partner
        return False

    def _prepare_partner_vals(self):
        self.ensure_one()
        partner_lang = self.env["res.partner"].sanitize_installed_lang(self.x_contact_language)
        return {
            "name": self.partner_name or self.contact_name or self.name,
            "company_type": "company",
            "email": self.email_from,
            "phone": self.phone,
            "mobile": self.mobile,
            "website": self.website,
            "lang": partner_lang,
            "x_contact_language": self.x_contact_language,
            "x_partner_business_sector": self.x_business_sector,
            "x_partner_priority_level": self.x_priority_level,
            "x_preferred_service_requested": self.x_service_requested,
            "x_partner_account_notes": self.x_strategic_comment,
        }

    def _ensure_partner_for_conversion(self):
        self.ensure_one()
        if self.partner_id:
            return self.partner_id
        partner = self._match_partner_from_lead()
        if not partner:
            partner = self.env["res.partner"].create(self._prepare_partner_vals())
        self.partner_id = partner.id
        return partner

    def _prepare_quote_note(self):
        self.ensure_one()
        lines = []
        if self.x_service_requested:
            label = dict(self._fields["x_service_requested"].selection).get(self.x_service_requested)
            lines.append(_("Service demande : %s") % label)
        if self.x_need_type:
            label = dict(self._fields["x_need_type"].selection).get(self.x_need_type)
            lines.append(_("Type de besoin : %s") % label)
        if self.x_strategic_comment:
            lines.append(_("Commentaire strategique : %s") % self.x_strategic_comment)
        return "\n".join(lines)

    def prepare_project_vals(self):
        self.ensure_one()
        return {
            "name": "%s - %s" % ((self.partner_id.name or self.partner_name or self.name), self.name),
            "partner_id": self.partner_id.id if self.partner_id else False,
            "user_id": self.user_id.id if self.user_id else self.env.user.id,
            "origin_opportunity_id": self.id,
            "service_requested": self.x_service_requested,
        }

    def action_prepare_won_conversion(self):
        SaleOrder = self.env["sale.order"]
        created_orders = self.env["sale.order"]
        for lead in self.filtered(lambda l: l.type == "opportunity"):
            partner = lead._ensure_partner_for_conversion()
            existing_order = SaleOrder.search(
                [
                    ("opportunity_id", "=", lead.id),
                    ("state", "in", ["draft", "sent", "sale"]),
                ],
                limit=1,
            )
            if existing_order:
                created_orders |= existing_order
                continue
            order = SaleOrder.create(
                {
                    "partner_id": partner.id,
                    "opportunity_id": lead.id,
                    "origin": lead.name,
                    "user_id": lead.user_id.id or self.env.user.id,
                    "client_order_ref": lead.name,
                    "note": lead._prepare_quote_note(),
                    "x_service_requested": lead.x_service_requested,
                }
            )
            created_orders |= order
        if len(created_orders) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("Devis prepare"),
                "res_model": "sale.order",
                "view_mode": "form",
                "res_id": created_orders.id,
            }
        if created_orders:
            return {
                "type": "ir.actions.act_window",
                "name": _("Devis prepares"),
                "res_model": "sale.order",
                "view_mode": "list,form",
                "domain": [("id", "in", created_orders.ids)],
            }
        return True

    def _get_digiplus_delete_blockers(self):
        self.ensure_one()
        blockers = []

        sale_orders = self.env["sale.order"].search_count(
            [
                ("opportunity_id", "=", self.id),
                ("state", "!=", "cancel"),
            ]
        )
        if sale_orders:
            blockers.append(_("devis ou commandes"))

        try:
            account_move_model = self.env["account.move"]
        except KeyError:
            account_move_model = False
        if account_move_model and "x_related_opportunity_id" in account_move_model._fields:
            account_moves = account_move_model.search_count(
                [
                    ("x_related_opportunity_id", "=", self.id),
                    ("state", "!=", "cancel"),
                ]
            )
        else:
            account_moves = 0
        if account_moves:
            blockers.append(_("factures"))

        try:
            project_model = self.env["project.project"]
        except KeyError:
            project_model = False
        if project_model and "origin_opportunity_id" in project_model._fields:
            projects = project_model.search_count([("origin_opportunity_id", "=", self.id)])
        else:
            projects = 0
        if projects:
            blockers.append(_("projets"))

        return blockers

    def action_delete_from_pipeline(self):
        self.ensure_one()
        blockers = self._get_digiplus_delete_blockers()
        if blockers:
            raise UserError(
                _("Suppression impossible : cette opportunite est encore liee a %s.")
                % ", ".join(blockers)
            )
        self.unlink()
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    @api.model_create_multi
    def create(self, vals_list):
        probability_map = self._get_stage_probability_map()
        updated_vals_list = []
        for vals in vals_list:
            vals = self._update_probability_from_stage(vals)
            if not vals.get("x_contact_language"):
                vals["x_contact_language"] = "fr_FR"
            if vals.get("stage_id") in probability_map and "probability" not in vals:
                vals["probability"] = probability_map[vals["stage_id"]]
            updated_vals_list.append(vals)
        leads = super().create(updated_vals_list)
        leads._validate_stage_requirements()
        won_stage = self._get_stage_ref("digiplus_crm.stage_won")
        if won_stage:
            leads.filtered(lambda lead: lead.stage_id.id == won_stage.id).action_prepare_won_conversion()
        return leads

    def write(self, vals):
        vals = self._update_probability_from_stage(vals)
        result = super().write(vals)
        if "stage_id" in vals:
            self._validate_stage_requirements()
            won_stage = self._get_stage_ref("digiplus_crm.stage_won")
            if won_stage:
                self.filtered(lambda lead: lead.stage_id.id == won_stage.id).action_prepare_won_conversion()
        return result

    @api.model
    def cron_create_missing_followup_activities(self):
        reminder_type = self.env.ref("digiplus_crm.activity_followup_reminder", raise_if_not_found=False)
        if not reminder_type:
            return True
        today = fields.Date.context_today(self)
        stage_won = self.env.ref("digiplus_crm.stage_won", raise_if_not_found=False)
        stage_lost = self.env.ref("digiplus_crm.stage_lost", raise_if_not_found=False)
        closed_ids = [stage.id for stage in (stage_won, stage_lost) if stage]
        leads = self.search(
            [
                ("type", "=", "opportunity"),
                ("stage_id", "not in", closed_ids),
                ("x_missing_next_action", "=", True),
                ("user_id", "!=", False),
            ]
        )
        for lead in leads:
            existing = self.env["mail.activity"].search(
                [
                    ("res_model", "=", "crm.lead"),
                    ("res_id", "=", lead.id),
                    ("activity_type_id", "=", reminder_type.id),
                    ("date_deadline", "=", today),
                ],
                limit=1,
            )
            if existing:
                continue
            lead.activity_schedule(
                activity_type_id=reminder_type.id,
                date_deadline=today + timedelta(days=1),
                summary=_("Relance a planifier"),
                note=_("Cette opportunite n'a aucune prochaine action planifiee."),
                user_id=lead.user_id.id,
            )
        return True
