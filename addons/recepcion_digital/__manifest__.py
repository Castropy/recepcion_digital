# -*- coding: utf-8 -*-
{
    'name': 'Recepción Digital',
    'version': '19.0.1.0.0',
    'summary': 'Digitalización de recepciones de materia prima agroindustrial',
    'description': 'Módulo para arroceras y agroindustrias de Portuguesa, Venezuela.',
    'author': 'Castropy',
    'category': 'Inventory',
    'depends': ['stock', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'data/recepcion_sequence.xml',
        'views/recepcion_arroz_views.xml',
        'views/recepcion_menu.xml',
        'reports/recepcion_arroz_report.xml',
        'reports/recepcion_arroz_template.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}