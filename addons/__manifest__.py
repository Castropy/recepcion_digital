{
    'name': 'Recepción Digital',
    'version': '17.0.1.0.0',
    'summary': 'Digitalización de recepciones de materia prima agroindustrial',
    'description': 'Módulo para arroceras y agroindustrias de Portuguesa, Venezuela.',
    'author': 'Castropy',
    'category': 'Inventory',
    'depends': ['stock', 'purchase', 'quality_control'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_lot_views.xml',
        'views/recepcion_menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}