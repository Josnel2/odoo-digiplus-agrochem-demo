from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


SECTOR_SELECTION = [
    ("industry", "Industrie"),
    ("distribution", "Distribution"),
    ("services", "Services"),
    ("education", "Education"),
    ("health", "Sante"),
    ("hospitality", "Hotellerie"),
    ("technology", "Technologies"),
]

CHANNEL_SELECTION = [
    ("email", "Email"),
    ("phone", "Telephone"),
    ("whatsapp", "WhatsApp"),
    ("onsite", "Visite"),
    ("linkedin", "LinkedIn"),
    ("referral", "Recommandation"),
    ("event", "Evenement"),
]

INTEREST_SELECTION = [
    ("cold", "Froid"),
    ("warm", "Tiede"),
    ("hot", "Chaud"),
]

PRIORITY_SELECTION = [
    ("low", "Faible"),
    ("medium", "Moyenne"),
    ("high", "Haute"),
    ("critical", "Critique"),
]

SEGMENT_SELECTION = [
    ("executive_pipeline", "Pilotage commercial"),
    ("erp_rollout", "Deploiement ERP"),
    ("data_governance", "Data & BI"),
    ("field_mobility", "Web & mobile"),
    ("support_recurring", "Support & maintenance"),
]


class CrmLead(models.Model):
    _inherit = "crm.lead"

    x_demo_sector = fields.Selection(SECTOR_SELECTION, string="Secteur d'activite")
    x_business_need = fields.Text(string="Besoin metier")
    x_geographic_zone = fields.Char(string="Zone geographique")
    x_entry_channel = fields.Selection(CHANNEL_SELECTION, string="Canal d'entree")
    x_interest_level = fields.Selection(INTEREST_SELECTION, string="Niveau d'interet", default="warm")
    x_recommended_solution = fields.Text(string="Solution recommandee")
    x_sage_saari_context = fields.Text(string="Contexte Sage Saari")
    x_bi_priority = fields.Selection(PRIORITY_SELECTION, string="Priorite BI", default="medium")
    x_whatsapp_followup = fields.Boolean(string="Suivi WhatsApp")
    x_demo_score = fields.Integer(string="Score commercial")
    x_expected_demo_value = fields.Float(string="Valeur projetee")
    x_next_decision_step = fields.Text(string="Prochaine etape de decision")
    x_demo_use_case = fields.Text(string="Cas d'usage prioritaire")
    x_agrochem_projection = fields.Text(string="Vision de transformation")
    x_stock_impact = fields.Text(string="Impact stock")
    x_purchase_impact = fields.Text(string="Impact achat")
    x_marketing_segment = fields.Selection(SEGMENT_SELECTION, string="Segment marketing")

    @api.model
    def _default_lead_score(self, interest):
        return {"cold": 45, "warm": 70, "hot": 90}.get(interest or "warm", 70)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            interest = vals.get("x_interest_level", "warm")
            vals.setdefault("x_demo_score", self._default_lead_score(interest))
            vals.setdefault("x_expected_demo_value", vals.get("expected_revenue", 0.0))
        records = super().create(vals_list)
        if not self.env.context.get("install_mode"):
            records._apply_business_automations()
        return records

    def write(self, vals):
        result = super().write(vals)
        if not self.env.context.get("install_mode"):
            self._apply_business_automations()
        return result

    def _apply_business_automations(self):
        self._ensure_sent_proposal_followup()
        self._ensure_hot_interest_activity()
        self._ensure_whatsapp_draft()

    def _schedule_unique_activity(self, xmlid, summary, note, days=0):
        activity_type = self.env.ref(xmlid, raise_if_not_found=False)
        if not activity_type:
            return
        for lead in self:
            existing = self.env["mail.activity"].search(
                [
                    ("res_model", "=", "crm.lead"),
                    ("res_id", "=", lead.id),
                    ("activity_type_id", "=", activity_type.id),
                    ("summary", "=", summary),
                ],
                limit=1,
            )
            if existing:
                continue
            lead.activity_schedule(
                activity_type_id=activity_type.id,
                summary=summary,
                note=note,
                date_deadline=fields.Date.today() + relativedelta(days=days),
                user_id=(lead.user_id or self.env.user).id,
            )

    def _ensure_sent_proposal_followup(self):
        sent_stage = self.env.ref("digiplus_crm.stage_proposal_sent", raise_if_not_found=False)
        if not sent_stage:
            return
        leads = self.filtered(lambda lead: lead.stage_id == sent_stage)
        leads._schedule_unique_activity(
            "digiplus_agrochem_demo.activity_proposal_followup",
            "Relance proposition commerciale",
            "Relancer le client 48h apres l'envoi de la proposition.",
            days=2,
        )

    def _ensure_hot_interest_activity(self):
        leads = self.filtered(lambda lead: lead.x_interest_level == "hot")
        leads._schedule_unique_activity(
            "digiplus_agrochem_demo.activity_priority_account",
            "Opportunite prioritaire",
            "Opportunite a fort enjeu: prioriser la relance commerciale et la validation de direction.",
            days=1,
        )

    def _ensure_whatsapp_draft(self):
        message_model = self.env["digiplus.whatsapp.message"].sudo()
        for lead in self.filtered("x_whatsapp_followup"):
            existing = message_model.search(
                [
                    ("crm_lead_id", "=", lead.id),
                    ("status", "in", ["draft", "ready", "sent", "delivered", "replied"]),
                ],
                limit=1,
            )
            if existing:
                continue
            message_model.create(
                {
                    "name": "Brouillon WhatsApp - %s" % lead.name,
                    "partner_id": lead.partner_id.id,
                    "crm_lead_id": lead.id,
                    "phone_number": lead.partner_id.mobile or lead.partner_id.phone or lead.phone,
                    "message_type": "followup",
                    "message_body": "Bonjour, DigiPlus vous partage le prochain point d'action concernant %s." % lead.name,
                    "status": "draft",
                }
            )

    def action_create_followup_activity(self):
        self._ensure_sent_proposal_followup()
        return True

    def action_create_priority_activity(self):
        self._ensure_hot_interest_activity()
        return True

    def action_prepare_whatsapp_draft(self):
        self._ensure_whatsapp_draft()
        return True
