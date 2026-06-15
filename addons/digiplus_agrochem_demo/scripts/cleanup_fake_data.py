"""Run this file from `odoo shell -d <db> < addons/.../cleanup_fake_data.py`."""

from collections import defaultdict


AMBIGUOUS = defaultdict(list)


def log_count(label, records):
    print(f"{label}: {len(records)}")


def add_ambiguous(model_name, record, reason):
    display = getattr(record, "display_name", False) or getattr(record, "name", False) or f"{model_name}:{record.id}"
    AMBIGUOUS[model_name].append((record.id, display, reason))


def unlink_records(model_name, records):
    deleted = 0
    for record in records:
        try:
            record.unlink()
            deleted += 1
        except Exception as exc:  # pylint: disable=broad-except
            add_ambiguous(model_name, record, str(exc))
    print(f"{model_name}: {deleted} supprimes")


def archive_records(model_name, records):
    archived = 0
    for record in records:
        try:
            if "active" in record._fields:
                record.write({"active": False})
                archived += 1
            else:
                add_ambiguous(model_name, record, "Champ active indisponible")
        except Exception as exc:  # pylint: disable=broad-except
            add_ambiguous(model_name, record, str(exc))
    print(f"{model_name}: {archived} archives")


def search_union(model, domains):
    records = env[model].browse()
    for domain in domains:
        records |= env[model].search(domain)
    return records


def cancel_pickings(pickings):
    done_pickings = pickings.filtered(lambda picking: picking.state == "done")
    for picking in done_pickings:
        add_ambiguous("stock.picking", picking, "Mouvement termine a verifier manuellement")

    cancellable = pickings - done_pickings
    for picking in cancellable.filtered(lambda picking: picking.state not in ("cancel",)):
        try:
            picking.action_cancel()
        except Exception as exc:  # pylint: disable=broad-except
            add_ambiguous("stock.picking", picking, f"Echec annulation: {exc}")

    return cancellable.filtered(lambda picking: picking.state == "cancel")


def cancel_purchase_orders(purchase_orders):
    cancellable = env["purchase.order"].browse()
    for order in purchase_orders:
        try:
            if order.state not in ("cancel",):
                if hasattr(order, "button_cancel"):
                    order.button_cancel()
            if order.state == "cancel":
                cancellable |= order
            else:
                add_ambiguous("purchase.order", order, f"Etat final non cancellable: {order.state}")
        except Exception as exc:  # pylint: disable=broad-except
            add_ambiguous("purchase.order", order, f"Echec annulation: {exc}")
    return cancellable


def cancel_sale_orders(sale_orders):
    cancellable = env["sale.order"].browse()
    for order in sale_orders:
        try:
            if order.state not in ("cancel",):
                order.action_cancel()
            if order.state == "cancel":
                cancellable |= order
            else:
                add_ambiguous("sale.order", order, f"Etat final non cancellable: {order.state}")
        except Exception as exc:  # pylint: disable=broad-except
            add_ambiguous("sale.order", order, f"Echec annulation: {exc}")
    return cancellable


def reset_invoices(invoices):
    removable = env["account.move"].browse()
    for invoice in invoices:
        try:
            if invoice.state == "posted" and hasattr(invoice, "button_draft"):
                invoice.button_draft()
            if invoice.state == "cancel" and hasattr(invoice, "button_draft"):
                invoice.button_draft()
            removable |= invoice
        except Exception as exc:  # pylint: disable=broad-except
            add_ambiguous("account.move", invoice, f"Echec retour brouillon: {exc}")
    return removable


demo_locations = search_union(
    "stock.location",
    [
        [("name", "ilike", "Demo Stock")],
        [("complete_name", "ilike", "Demo Stock")],
    ],
)
demo_quants = env["stock.quant"].search([("location_id", "in", demo_locations.ids)]) if demo_locations else env["stock.quant"].browse()
demo_pickings = search_union(
    "stock.picking",
    [
        [("name", "ilike", "DEMO-STOCK%")],
        [("origin", "ilike", "DEMO-STOCK%")],
        [("x_demo_comment", "ilike", "demonstration")],
        [("x_demo_comment", "ilike", "AGROCHEM")],
        [("location_id", "in", demo_locations.ids)] if demo_locations else [("id", "=", 0)],
        [("location_dest_id", "in", demo_locations.ids)] if demo_locations else [("id", "=", 0)],
    ],
)
demo_whatsapp = search_union(
    "digiplus.whatsapp.message",
    [
        [("name", "ilike", "Message WhatsApp demo%")],
        [("api_reference", "ilike", "DEMO-WA%")],
        [("message_body", "ilike", "projection AGROCHEM")],
        [("message_body", "ilike", "demonstration")],
    ],
)
demo_activities = search_union(
    "mail.activity",
    [
        [("summary", "ilike", "Suivi demo%")],
        [("note", "ilike", "projection AGROCHEM")],
        [("note", "ilike", "demonstration")],
    ],
)
demo_leads = search_union(
    "crm.lead",
    [
        [("name", "ilike", "AGROCHEM%")],
        [("name", "ilike", "%Demonstration%")],
        [("x_agrochem_projection", "ilike", "AGROCHEM")],
        [("x_demo_use_case", "ilike", "demonstration")],
    ],
)
demo_sale_orders = search_union(
    "sale.order",
    [
        [("name", "ilike", "DEMO-SQ%")],
        [("x_agrochem_projection", "ilike", "AGROCHEM")],
    ],
)
demo_purchase_orders = search_union(
    "purchase.order",
    [
        [("name", "ilike", "DEMO-PO%")],
        [("x_agrochem_purchase_context", "ilike", "AGROCHEM")],
    ],
)
demo_invoices = search_union(
    "account.move",
    [
        [("invoice_origin", "ilike", "DEMO-SQ%")],
        [("x_sage_saari_reference", "ilike", "SAGE-DEMO%")],
        [("x_integration_comment", "ilike", "demonstratif")],
    ],
)
fake_products = search_union(
    "product.product",
    [
        [("default_code", "ilike", "DPA-PRD%")],
        [("name", "ilike", "AGROCHEM%")],
    ],
)
fake_partners = search_union(
    "res.partner",
    [
        [("name", "ilike", "AGROCHEM%")],
        [("email", "ilike", "%@agrochem-ac.cm")],
    ],
)

print("=== INVENTAIRE AVANT SUPPRESSION ===")
log_count("stock.location Demo Stock", demo_locations)
log_count("stock.quant sur emplacements demo", demo_quants)
log_count("stock.picking DEMO-STOCK", demo_pickings)
log_count("messages WhatsApp demo", demo_whatsapp)
log_count("activites demo", demo_activities)
log_count("opportunites demo", demo_leads)
log_count("devis demo", demo_sale_orders)
log_count("achats demo", demo_purchase_orders)
log_count("factures demo", demo_invoices)
log_count("produits fake explicites", fake_products)
log_count("partenaires fake explicites", fake_partners)

print("\n=== SUPPRESSION AUTO ===")
cancelled_pickings = cancel_pickings(demo_pickings)
unlink_records("digiplus.whatsapp.message", demo_whatsapp)
unlink_records("mail.activity", demo_activities)
unlink_records("crm.lead", demo_leads)
unlink_records("account.move", reset_invoices(demo_invoices))
unlink_records("sale.order", cancel_sale_orders(demo_sale_orders))
unlink_records("purchase.order", cancel_purchase_orders(demo_purchase_orders))
unlink_records("stock.picking", cancelled_pickings)
unlink_records("stock.quant", demo_quants)
unlink_records("stock.location", demo_locations)

safe_products = env["product.product"].browse()
for product in fake_products:
    sale_lines = env["sale.order.line"].search_count([("product_id", "=", product.id)])
    purchase_lines = env["purchase.order.line"].search_count([("product_id", "=", product.id)])
    invoice_lines = env["account.move.line"].search_count([("product_id", "=", product.id)])
    move_lines = env["stock.move"].search_count([("product_id", "=", product.id)])
    if sale_lines or purchase_lines or invoice_lines or move_lines:
        add_ambiguous(
            "product.product",
            product,
            f"Encore lie a des documents: sale={sale_lines}, purchase={purchase_lines}, invoice={invoice_lines}, stock={move_lines}",
        )
    else:
        safe_products |= product
archive_records("product.product", safe_products)

safe_partners = env["res.partner"].browse()
for partner in fake_partners:
    lead_count = env["crm.lead"].search_count([("partner_id", "=", partner.id)])
    sale_count = env["sale.order"].search_count([("partner_id", "=", partner.id)])
    purchase_count = env["purchase.order"].search_count([("partner_id", "=", partner.id)])
    invoice_count = env["account.move"].search_count([("partner_id", "=", partner.id)])
    picking_count = env["stock.picking"].search_count([("partner_id", "=", partner.id)])
    if lead_count or sale_count or purchase_count or invoice_count or picking_count:
        add_ambiguous(
            "res.partner",
            partner,
            f"Encore lie a des documents: leads={lead_count}, sale={sale_count}, purchase={purchase_count}, invoice={invoice_count}, stock={picking_count}",
        )
    else:
        safe_partners |= partner
archive_records("res.partner", safe_partners)

print("\n=== A VALIDER ===")
if not AMBIGUOUS:
    print("Aucun cas ambigu.")
else:
    for model_name in sorted(AMBIGUOUS):
        print(f"\n{model_name}")
        for rec_id, display, reason in AMBIGUOUS[model_name]:
            print(f"- [{rec_id}] {display}: {reason}")

env.cr.commit()
print("\nNettoyage termine. Pensez a verifier les cas 'A VALIDER' avant toute livraison.")
