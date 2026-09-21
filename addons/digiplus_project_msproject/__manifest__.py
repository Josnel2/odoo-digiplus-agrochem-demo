# -*- coding: utf-8 -*-
{
    'name': 'Digiplus MS Project Integration',
    'version': '17.0.1.0.0',
    'summary': 'Integration Microsoft Project: Gantt, WBS, Dependencies and XML Import',
    'sequence': 10,
    'description': """
        Ce module étend les fonctionnalités de projet d'Odoo pour intégrer
        les concepts de MS Project (WBS hiérarchique, Dépendances complexes,
        Nivellement, et import XML).
    """,
    'category': 'Services/Project',
    'author': 'Genius Electronics / Digiplus',
    'depends': ['project', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/project_task_views.xml',
        'wizard/import_msproject_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
