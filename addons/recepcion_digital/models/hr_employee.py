# -*- coding: utf-8 -*-
from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    area_trabajo = fields.Selection(
        selection=[
            ('romana', 'Romana / Báscula'),
            ('laboratorio', 'Laboratorio de Calidad'),
            ('administracion', 'Administración / Gerencia'),
            ('patio', 'Patio / Descarga'),
        ],
        string='Área de Trabajo',
        default='romana',
        required=True,
        help='Área operativa asignada al colaborador dentro de la planta.'
    )