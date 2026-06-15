"""
Script Odoo shell pour nettoyer les fake data CRM sans supprimer les cas ambigus.

Usage:
odoo shell -d <db> < /mnt/extra-addons/digiplus_crm/scripts/cleanup_crm_fake_data.py
"""

from odoo import fields


KEYWORDS = ["demo", "test", "fake", "sample"]
EXPLICIT_PREFIXES = ["demo", "test", "fake", "sample", "xxx"]


def normalize(value):
    return (value or "").strip().lower()


def looks_explicitly_fake(value):
    normalized = normalize(value)
    return any(normalized.startswith(prefix) for prefix in EXPLICIT_PREFIXES)


def looks_suspicious(value):
    normalized = normalize(value)
    return any(keyword in normalized for keyword in KEYWORDS)


def print_records(title, records, fields_to_show):
    print("\n%s: %s" % (title, len(records)))
    for record in records:
        values = []
        for field_name in fields_to_show:
            values.append("%s=%s" % (field_name, getattr(record, field_name, False)))
        print(" - %s" % ", ".join(values))


Lead = env["crm.lead"]
Partner = env["res.partner"]
Activity = env["mail.activity"]
Source = env["utm.source"]
Tag = env["crm.tag"]

all_leads = Lead.search([("type", "=", "opportunity")])
all_partners = Partner.search([])
all_activities = Activity.search([("res_model", "=", "crm.lead")])

explicit_fake_leads = all_leads.filtered(
    lambda lead: looks_explicitly_fake(lead.name)
    or looks_explicitly_fake(lead.partner_name)
    or looks_explicitly_fake(lead.email_from)
)
ambiguous_leads = (all_leads.filtered(
    lambda lead: not lead in explicit_fake_leads
    and (
        looks_suspicious(lead.name)
        or looks_suspicious(lead.partner_name)
        or looks_suspicious(lead.description)
    )
))

explicit_fake_partners = all_partners.filtered(
    lambda partner: looks_explicitly_fake(partner.name)
    or looks_explicitly_fake(partner.email)
)
ambiguous_partners = all_partners.filtered(
    lambda partner: partner not in explicit_fake_partners
    and (
        looks_suspicious(partner.name)
        or looks_suspicious(partner.email)
        or looks_suspicious(partner.comment)
    )
)

explicit_fake_activities = all_activities.filtered(
    lambda activity: looks_explicitly_fake(activity.summary) or looks_explicitly_fake(activity.note)
)
ambiguous_activities = all_activities.filtered(
    lambda activity: activity not in explicit_fake_activities
    and (looks_suspicious(activity.summary) or looks_suspicious(activity.note))
)

explicit_fake_sources = Source.search([]).filtered(lambda source: looks_explicitly_fake(source.name))
explicit_fake_tags = Tag.search([]).filtered(lambda tag: looks_explicitly_fake(tag.name))

print_records("Opportunites explicitement fake", explicit_fake_leads, ["id", "name", "partner_name"])
print_records("Opportunites a valider", ambiguous_leads, ["id", "name", "partner_name"])
print_records("Partenaires explicitement fake", explicit_fake_partners, ["id", "name", "email"])
print_records("Partenaires a valider", ambiguous_partners, ["id", "name", "email"])
print_records("Activites explicitement fake", explicit_fake_activities, ["id", "summary"])
print_records("Activites a valider", ambiguous_activities, ["id", "summary"])
print_records("Sources explicitement fake", explicit_fake_sources, ["id", "name"])
print_records("Tags explicitement fake", explicit_fake_tags, ["id", "name"])

print("\nSuppression des fake data explicites...")

for activity in explicit_fake_activities:
    activity.unlink()

for lead in explicit_fake_leads:
    if lead.stage_id and lead.stage_id.name.lower() not in ["gagne", "perdu"]:
        for activity in lead.activity_ids:
            activity.unlink()
    lead.unlink()

for partner in explicit_fake_partners:
    linked_opportunities = Lead.search_count([("partner_id", "=", partner.id)])
    linked_orders = env["sale.order"].search_count([("partner_id", "child_of", partner.id)])
    if linked_opportunities or linked_orders or partner.child_ids:
        print(" - Partenaire ambigu preserve: id=%s, name=%s" % (partner.id, partner.name))
        continue
    partner.unlink()

explicit_fake_sources.unlink()
explicit_fake_tags.unlink()

print("\nNettoyage termine le %s." % fields.Datetime.now())
print("Les enregistrements listes comme 'a valider' n'ont pas ete modifies.")
