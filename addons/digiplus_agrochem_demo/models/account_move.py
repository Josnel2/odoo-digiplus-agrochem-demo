from odoo import _, api, fields, models
from odoo.exceptions import UserError


EXPORT_SELECTION = [
    ("not_concerned", "Non concerne par export externe"),
    ("not_exported", "Non exporte"),
    ("ready", "Pret pour export externe"),
    ("exported", "Exporte"),
    ("error", "Erreur export"),
]

WORKFLOW_ORIGIN_SELECTION = [
    ("crm", "CRM vers devis"),
    ("sale", "Devis / commande"),
    ("manual", "Facturation manuelle"),
]

CUSTOMER_MOVE_TYPES = ("out_invoice", "out_refund")


class AccountMove(models.Model):
    _inherit = "account.move"

    x_related_sale_order_id = fields.Many2one(
        "sale.order",
        string="Devis / commande source",
        compute="_compute_digiplus_workflow_context",
        store=True,
        index=True,
    )
    x_related_opportunity_id = fields.Many2one(
        "crm.lead",
        string="Opportunite source",
        compute="_compute_digiplus_workflow_context",
        store=True,
        index=True,
    )
    x_workflow_origin = fields.Selection(
        WORKFLOW_ORIGIN_SELECTION,
        string="Origine du workflow",
        compute="_compute_digiplus_workflow_context",
        store=True,
    )
    x_sage_saari_export_status = fields.Selection(
        EXPORT_SELECTION, string="Statut export externe", default="not_concerned"
    )
    x_sage_saari_reference = fields.Char(string="Reference export externe")
    x_integration_comment = fields.Text(string="Commentaire export / integration")

    @api.depends(
        "invoice_origin",
        "partner_id",
        "move_type",
        "invoice_line_ids.sale_line_ids.order_id",
        "invoice_line_ids.sale_line_ids.order_id.opportunity_id",
    )
    def _compute_digiplus_workflow_context(self):
        SaleOrder = self.env["sale.order"]
        for move in self:
            sale_order = move.invoice_line_ids.mapped("sale_line_ids.order_id")[:1]
            if not sale_order and move.invoice_origin:
                domain = [("name", "=", move.invoice_origin)]
                if move.partner_id:
                    domain.append(("partner_id", "=", move.partner_id.id))
                sale_order = SaleOrder.search(domain, limit=1)

            move.x_related_sale_order_id = sale_order
            move.x_related_opportunity_id = sale_order.opportunity_id

            if sale_order and sale_order.opportunity_id:
                move.x_workflow_origin = "crm"
            elif sale_order:
                move.x_workflow_origin = "sale"
            elif move.move_type in CUSTOMER_MOVE_TYPES:
                move.x_workflow_origin = "manual"
            else:
                move.x_workflow_origin = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            move_type = vals.get("move_type")
            if move_type in CUSTOMER_MOVE_TYPES and not vals.get("x_sage_saari_export_status"):
                vals["x_sage_saari_export_status"] = "not_exported"
        return super().create(vals_list)

    def _build_digiplus_integration_comment(self):
        self.ensure_one()
        parts = []
        if self.x_related_opportunity_id:
            parts.append(_("Opportunite CRM : %s") % self.x_related_opportunity_id.display_name)
        if self.x_related_sale_order_id:
            parts.append(_("Devis source : %s") % self.x_related_sale_order_id.name)
        if self.invoice_origin and not self.x_related_sale_order_id:
            parts.append(_("Origine facture : %s") % self.invoice_origin)
        return " | ".join(parts)

    def action_mark_ready_for_export(self):
        for move in self:
            if move.move_type not in CUSTOMER_MOVE_TYPES:
                raise UserError(_("Seules les factures clients peuvent etre preparees pour l'export."))
            if move.state == "cancel":
                raise UserError(_("Une facture annulee ne peut pas etre preparee pour l'export."))
            if not move.partner_id:
                raise UserError(_("La facture doit avoir un client avant preparation comptable."))
            if not move.invoice_line_ids:
                raise UserError(_("La facture doit avoir au moins une ligne avant preparation comptable."))

            vals = {"x_sage_saari_export_status": "ready"}
            comment = move._build_digiplus_integration_comment()
            if comment and not move.x_integration_comment:
                vals["x_integration_comment"] = comment
            move.write(vals)
        return True

    def action_mark_ready_for_sage(self):
        return self.action_mark_ready_for_export()

    def action_post(self):
        result = super().action_post()
        moves_to_prepare = self.filtered(
            lambda move: move.move_type in CUSTOMER_MOVE_TYPES
            and move.state == "posted"
            and move.x_sage_saari_export_status in ("not_concerned", "not_exported", "error")
            and (move.x_related_sale_order_id or move.invoice_origin)
        )
        if moves_to_prepare:
            moves_to_prepare.action_mark_ready_for_export()
        return result

    def action_post_digiplus_workflow(self):
        return self.action_post()

    def action_reset_to_draft_digiplus_workflow(self):
        return self.button_draft()

    def action_open_related_sale_order(self):
        self.ensure_one()
        if not self.x_related_sale_order_id:
            return True
        return {
            "type": "ir.actions.act_window",
            "name": _("Devis source"),
            "res_model": "sale.order",
            "view_mode": "form",
            "res_id": self.x_related_sale_order_id.id,
        }

    def action_open_related_opportunity(self):
        self.ensure_one()
        if not self.x_related_opportunity_id:
            return True
        return {
            "type": "ir.actions.act_window",
            "name": _("Opportunite source"),
            "res_model": "crm.lead",
            "view_mode": "form",
            "res_id": self.x_related_opportunity_id.id,
        }
