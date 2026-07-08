from odoo import _, fields, models
from odoo.exceptions import UserError


PROPOSAL_SELECTION = [
    ("modular", "Modulaire"),
    ("bundle", "Pack"),
    ("pilot", "Pilote"),
    ("rollout", "Deploiement"),
]

DECISION_SELECTION = [
    ("draft", "Brouillon"),
    ("in_review", "En revision"),
    ("sent", "Envoye"),
    ("approved", "Approuve"),
    ("won", "Gagne"),
]

ACCOUNTING_FLOW_SELECTION = [
    ("quotation", "Devis"),
    ("order_confirmed", "Commande confirmee"),
    ("draft_invoice", "Facture brouillon"),
    ("posted_invoice", "Facture validee"),
    ("ready_for_export", "Prete pour export"),
    ("exported", "Exportee"),
]

EXPORT_SELECTION = [
    ("not_concerned", "Non concerne par export externe"),
    ("not_exported", "Non exporte"),
    ("ready", "Pret pour export externe"),
    ("exported", "Exporte"),
    ("error", "Erreur export"),
]


class SaleOrder(models.Model):
    _inherit = "sale.order"

    x_demo_proposal_type = fields.Selection(PROPOSAL_SELECTION, string="Mode de proposition")
    x_related_demo_axis = fields.Char(string="Axes de la proposition")
    x_agrochem_projection = fields.Text(string="Vision de transformation")
    x_decision_status = fields.Selection(DECISION_SELECTION, string="Statut de decision", default="draft")
    x_workflow_invoice_ids = fields.Many2many(
        "account.move",
        string="Factures liees",
        compute="_compute_digiplus_accounting_snapshot",
    )
    x_workflow_invoice_count = fields.Integer(
        string="Nombre de factures",
        compute="_compute_digiplus_accounting_snapshot",
    )
    x_last_invoice_id = fields.Many2one(
        "account.move",
        string="Derniere facture",
        compute="_compute_digiplus_accounting_snapshot",
    )
    x_accounting_flow_status = fields.Selection(
        ACCOUNTING_FLOW_SELECTION,
        string="Statut devis -> comptabilite",
        compute="_compute_digiplus_accounting_snapshot",
    )
    x_accounting_export_status = fields.Selection(
        EXPORT_SELECTION,
        string="Statut export comptable",
        compute="_compute_digiplus_accounting_snapshot",
    )

    def _get_digiplus_related_invoices(self):
        self.ensure_one()
        return self.env["account.move"].search(
            [
                ("move_type", "in", ["out_invoice", "out_refund"]),
                "|",
                ("x_related_sale_order_id", "=", self.id),
                ("invoice_origin", "=", self.name),
            ],
            order="invoice_date desc, id desc",
        )

    def _compute_digiplus_accounting_snapshot(self):
        for order in self:
            invoices = order._get_digiplus_related_invoices()
            latest_invoice = invoices[:1]

            order.x_workflow_invoice_ids = invoices
            order.x_workflow_invoice_count = len(invoices)
            order.x_last_invoice_id = latest_invoice
            order.x_accounting_export_status = latest_invoice.x_sage_saari_export_status

            if not invoices:
                order.x_accounting_flow_status = (
                    "order_confirmed" if order.state in ("sale", "done") else "quotation"
                )
                continue

            if latest_invoice.x_sage_saari_export_status == "exported":
                order.x_accounting_flow_status = "exported"
            elif latest_invoice.x_sage_saari_export_status == "ready":
                order.x_accounting_flow_status = "ready_for_export"
            elif latest_invoice.state == "posted":
                order.x_accounting_flow_status = "posted_invoice"
            else:
                order.x_accounting_flow_status = "draft_invoice"

    def action_confirm_digiplus_workflow(self):
        orders_to_confirm = self.filtered(lambda order: order.state in ("draft", "sent"))
        result = True
        if orders_to_confirm:
            result = orders_to_confirm.action_confirm()
            orders_to_confirm.filtered(lambda order: order.x_decision_status != "won").write(
                {"x_decision_status": "won"}
            )
        return result

    def action_create_workflow_invoice(self):
        self.ensure_one()
        if self.state in ("draft", "sent"):
            self.action_confirm_digiplus_workflow()

        existing_invoices = self._get_digiplus_related_invoices().filtered(lambda move: move.state != "cancel")
        if existing_invoices and self.invoice_status == "invoiced":
            return self.action_open_workflow_invoices()

        created_invoices = self._create_invoices()
        if created_invoices:
            if len(created_invoices) == 1:
                return {
                    "type": "ir.actions.act_window",
                    "name": _("Facture client"),
                    "res_model": "account.move",
                    "view_mode": "form",
                    "res_id": created_invoices.id,
                }
            return {
                "type": "ir.actions.act_window",
                "name": _("Factures clients"),
                "res_model": "account.move",
                "view_mode": "list,form",
                "domain": [("id", "in", created_invoices.ids)],
            }

        if existing_invoices:
            return self.action_open_workflow_invoices()

        raise UserError(_("Aucune facture n'a pu etre creee depuis ce devis."))

    def action_open_workflow_invoices(self):
        self.ensure_one()
        invoices = self._get_digiplus_related_invoices()
        if not invoices:
            return True
        if len(invoices) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("Facture client"),
                "res_model": "account.move",
                "view_mode": "form",
                "res_id": invoices.id,
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("Factures clients"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", invoices.ids)],
        }
