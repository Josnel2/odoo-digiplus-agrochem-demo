{
    "name": "DigiPlus Project Delivery",
    "summary": "Gestion de projets, taches, alertes, suivi du temps et reporting pour DigiPlus.",
    "version": "18.0.1.0.0",
    "category": "Services/Project",
    "author": "DigiPlus Consulting",
    "license": "LGPL-3",
    "depends": [
        "digiplus_crm",
        "sale_timesheet",
    ],
    "data": [
        "data/project_cron_data.xml",
        "views/project_project_views.xml",
        "views/project_task_views.xml",
        "views/res_partner_views.xml",
        "views/crm_lead_views.xml",
        "views/project_menu_views.xml",
        "reports/project_progress_report.xml",
    ],
    "installable": True,
    "application": False,
}
