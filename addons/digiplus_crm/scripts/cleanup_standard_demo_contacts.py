"""
Nettoie les contacts / utilisateurs de demo Odoo et remet les cartes Contacts
dans un contexte DigiPlus / Afrique centrale.

Usage:
odoo shell -d <db> < /mnt/extra-addons/digiplus_crm/scripts/cleanup_standard_demo_contacts.py
"""

DEMO_USER_LOGINS = {"demo", "portal"}
DEMO_COMPANY_NAMES = {
    "acme corporation",
    "azure interior",
    "gemini furniture",
    "lumber inc",
    "openwood",
    "ready mat",
    "the jackson group",
    "wood corner",
    "yourcompany",
}
DEMO_EMAIL_FRAGMENTS = [
    "@example.com",
    "@example.net",
    "@yourcompany.example",
    "@agrolait.com",
    "@armyspy.com",
    "@tech.info",
    "@company.example",
]
AFRICAN_CONTACTS = [
    {
        "company": "Vision Retail Group",
        "name": "Fatima Ndzi",
        "function": "Directrice commerciale",
        "email": "fatima.ndzi@visionretail.cm",
        "mobile": "+237690110111",
    },
    {
        "company": "Nova Manufacturing Cameroon",
        "name": "Serge Ekani",
        "function": "Directeur general",
        "email": "serge.ekani@nova-mfg.cm",
        "mobile": "+237690110112",
    },
    {
        "company": "Orbit Finance Advisory",
        "name": "Nadia Mbappe",
        "function": "Responsable transformation",
        "email": "nadia.mbappe@orbitfinance.cm",
        "mobile": "+237690110113",
    },
    {
        "company": "Horizon Health Services",
        "name": "Dr Mebenga",
        "function": "Directeur des operations",
        "email": "dr.mebenga@horizonhealth.cm",
        "mobile": "+237690110114",
    },
    {
        "company": "Campus Plus Academy",
        "name": "Julien Tchouta",
        "function": "Responsable admissions",
        "email": "julien.tchouta@campusplus.cm",
        "mobile": "+237690110115",
    },
    {
        "company": "BlueWave Hospitality",
        "name": "Clarisse Kotto",
        "function": "Directrice experience client",
        "email": "clarisse.kotto@bluewave.cm",
        "mobile": "+237690110116",
    },
    {
        "company": "GreenPath Logistics",
        "name": "Andre Nsom",
        "function": "Responsable support",
        "email": "andre.nsom@greenpath.cm",
        "mobile": "+237690110117",
    },
    {
        "company": "Tekno Retail Cameroon",
        "name": "Maurice Bikoi",
        "function": "Directeur commercial",
        "email": "maurice.bikoi@teknoretail.cm",
        "mobile": "+237690110118",
    },
]


def norm(value):
    return (value or "").strip().lower()


def is_demo_email(email):
    lowered = norm(email)
    return any(fragment in lowered for fragment in DEMO_EMAIL_FRAGMENTS)


def is_demo_partner(partner):
    if norm(partner.name) in DEMO_COMPANY_NAMES:
        return True
    if partner.parent_id and norm(partner.parent_id.name) in DEMO_COMPANY_NAMES:
        return True
    if is_demo_email(partner.email):
        return True
    if is_demo_email(partner.email_formatted):
        return True
    if norm(partner.website).endswith(".example.com"):
        return True
    return False


def clear_images(partner):
    image_fields = [name for name in partner._fields if name.startswith("image_")]
    if image_fields:
        partner.write({field_name: False for field_name in image_fields})


def get_active_users_for_partner(partner):
    return Users.search([("partner_id", "=", partner.id), ("active", "=", True)])


Partner = env["res.partner"]
Users = env["res.users"]
Company = env.company
cm_country = env.ref("base.cm", raise_if_not_found=False)
fr_lang = env["res.lang"].search([("code", "=", "fr_FR")], limit=1)
installed_fr_lang = fr_lang.code if fr_lang else False
fallback_lang = Partner.get_fallback_installed_lang(preferred_lang=installed_fr_lang)

print("=== Nettoyage des contacts de demo standard Odoo ===")

# Recaler l'entreprise courante sur DigiPlus si elle est encore en demo.
if norm(Company.name) == "yourcompany":
    Company.write({"name": "DigiPlus Consulting"})
    print("Societe renommee: DigiPlus Consulting")

company_partner = Company.partner_id
if company_partner and norm(company_partner.name) == "yourcompany":
    company_partner.write(
        {
            "name": "DigiPlus Consulting",
            "city": "Douala",
            "country_id": cm_country.id if cm_country else False,
            "active": True,
        }
    )
    clear_images(company_partner)
    print("Fiche partenaire societe mise a jour: DigiPlus Consulting")

# Neutraliser les utilisateurs de demo visibles dans Contacts.
demo_users = Users.search([("login", "in", list(DEMO_USER_LOGINS))])
print("Utilisateurs demo trouves:", len(demo_users))
for user in demo_users:
    user.write({"active": False})
    if user.partner_id:
        clear_images(user.partner_id)
        user.partner_id.write({"active": False})
    print(" - utilisateur archive:", user.login)

# Renommer l'admin si le nom est encore celui de la demo Odoo.
admin_user = Users.search([("login", "=", "admin")], limit=1)
if admin_user:
    if admin_user.lang != fallback_lang:
        admin_user.write({"lang": fallback_lang})
        print("Langue admin corrigee:", fallback_lang)
    if norm(admin_user.name) == "mitchell admin":
        admin_user.write({"name": "DigiPlus Admin"})
        print("Utilisateur admin renomme: DigiPlus Admin")
    if admin_user.partner_id:
        clear_images(admin_user.partner_id)
        admin_partner_vals = {
            "active": True,
            "city": "Douala",
            "country_id": cm_country.id if cm_country else False,
            "lang": installed_fr_lang,
        }
        if norm(admin_user.partner_id.name) == "mitchell admin":
            admin_partner_vals["name"] = "DigiPlus Admin"
        if is_demo_email(admin_user.partner_id.email):
            admin_partner_vals["email"] = "admin@digiplus.cm"
        admin_user.partner_id.write(admin_partner_vals)
        print("Partenaire admin nettoye:", admin_user.partner_id.display_name)

demo_partners = Partner.search([]).filtered(is_demo_partner)
print("Partenaires demo trouves:", len(demo_partners))
for partner in demo_partners:
    if company_partner and partner.id == company_partner.id:
        continue
    active_users = get_active_users_for_partner(partner)
    if active_users:
        clear_images(partner)
        partner.write({"active": True})
        print(
            " - partenaire preserve car lie a un utilisateur actif:",
            partner.display_name,
            "=>",
            ", ".join(active_users.mapped("login")),
        )
        continue
    clear_images(partner)
    partner.write({"active": False})
    print(" - partenaire archive:", partner.display_name)

# Creer des contacts de presentation a consonance locale pour les comptes DigiPlus.
print("Creation / mise a jour des contacts de presentation africains...")
for item in AFRICAN_CONTACTS:
    company = Partner.search(
        [("name", "=", item["company"]), ("is_company", "=", True)],
        limit=1,
    )
    if not company:
        print(" - societe absente, ignoree:", item["company"])
        continue
    vals = {
        "name": item["name"],
        "parent_id": company.id,
        "type": "contact",
        "company_type": "person",
        "function": item["function"],
        "email": item["email"],
        "mobile": item["mobile"],
        "phone": item["mobile"],
        "city": company.city,
        "country_id": company.country_id.id,
        "lang": installed_fr_lang,
        "active": True,
    }
    existing = Partner.search(
        [("parent_id", "=", company.id), ("name", "=", item["name"])],
        limit=1,
    )
    if existing:
        existing.write(vals)
        clear_images(existing)
        print(" - contact mis a jour:", existing.display_name)
    else:
        created = Partner.create(vals)
        clear_images(created)
        print(" - contact cree:", created.display_name)

env.cr.commit()
print("=== Nettoyage termine ===")
