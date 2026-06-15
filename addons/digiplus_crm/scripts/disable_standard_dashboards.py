"""
Masque les menus/actions de l'application standard Dashboards si elle n'est pas
retenue pour la presentation DigiPlus.

Usage:
odoo shell -d <db> < /mnt/extra-addons/digiplus_crm/scripts/disable_standard_dashboards.py
"""

MENU_NAMES = {"dashboards", "dashboard"}
RES_MODELS = {
    "spreadsheet.dashboard",
    "spreadsheet.dashboard.group",
    "board.board",
}


def norm(value):
    return (value or "").strip().lower()


Menu = env["ir.ui.menu"].sudo()
ActionWindow = env["ir.actions.act_window"].sudo()
modules = env["ir.module.module"].sudo().search([("name", "ilike", "dashboard")])

print("=== Analyse des modules dashboard ===")
for module in modules:
    print(" -", module.name, module.state)

print("\n=== Desactivation des actions dashboard standard ===")
actions = ActionWindow.search([("res_model", "in", list(RES_MODELS))])
for action in actions:
    if "active" in action._fields:
        action.write({"active": False})
    print(" - action neutralisee:", action.name, "/", action.res_model)

print("\n=== Desactivation des menus dashboard standard ===")
menus = Menu.search([]).filtered(
    lambda menu: (
        norm(menu.name) in MENU_NAMES
        or (menu.action and getattr(menu.action, "res_model", False) in RES_MODELS)
        or (menu.parent_id and norm(menu.parent_id.name) in MENU_NAMES)
    )
)
for menu in menus:
    if "active" in menu._fields:
        menu.write({"active": False})
    print(" - menu neutralise:", menu.complete_name)

print("\n=== Nettoyage des dashboards standard si le modele existe ===")
registry_models = env.registry.models
for model_name in ("spreadsheet.dashboard", "spreadsheet.dashboard.group"):
    if model_name not in registry_models:
        continue
    records = env[model_name].sudo().search([])
    for record in records:
        if "active" in record._fields:
            record.write({"active": False})
            print(" - record archive:", model_name, getattr(record, "display_name", record.id))
        else:
            print(" - record conserve (pas de champ active):", model_name, getattr(record, "display_name", record.id))

env.cr.commit()
print("\n=== Dashboards standards neutralises ===")
