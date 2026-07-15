{
    "name": "DigiPlus AI Assistant",
    "summary": "Generation et validation humaine de projets DigiPlus assistes par IA",
    "version": "18.0.1.0.0",
    "category": "Services/Project",
    "author": "DigiPlus Consulting",
    "license": "LGPL-3",
    "depends": ["digiplus_project", "mail"],
    "data": [
        "security/ai_assistant_security.xml",
        "security/ir.model.access.csv",
        "views/ai_project_draft_views.xml",
        "views/ai_project_generate_wizard_views.xml",
        "views/res_config_settings_views.xml",
        "views/menu_views.xml",
    ],
    "external_dependencies": {"python": []},
    "assets": {
        "web.assets_backend": [
            "digiplus_ai_assistant/static/src/js/ai_chat.js",
            "digiplus_ai_assistant/static/src/xml/ai_chat.xml",
            "digiplus_ai_assistant/static/src/scss/ai_chat.scss",
        ],
    },
    "installable": True,
    "application": True,
}
