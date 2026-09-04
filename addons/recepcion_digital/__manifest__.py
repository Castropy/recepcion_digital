# -*- coding: utf-8 -*-
{
    'name': 'Recepción Digital',
    'version': '19.0.1.0.0',
    'summary': 'Digitalización de recepciones de materia prima agroindustrial',
    'description': """
Módulo de Gestión de Recepción Digital de Materia Prima
=========================================================
Diseñado para la recepción de arroz paddy, báscula, laboratorio y deducciones 
en la industria agroindustrial.
    """,
    'author': 'Castropy',
    'category': 'Supply Chain/Inventory',
    'depends': [
        'base',
        'mail',
        'stock',
        'purchase',
        'hr',
    ],
    'data': [
        'security/recepcion_security.xml',
        'security/ir.model.access.csv',
        'data/recepcion_sequence.xml',
        'views/recepcion_arroz_views.xml',
        'views/recepcion_menu.xml',
        'views/res_partner_views.xml',
        'views/res_users_views.xml',
        'reports/recepcion_arroz_report.xml',
        'reports/recepcion_arroz_template.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}