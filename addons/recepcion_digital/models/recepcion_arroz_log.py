# -*- coding: utf-8 -*-
from odoo import models, fields

class RecepcionArrozLog(models.Model):
    """
    Modelo de auditoría para registrar las modificaciones realizadas
    sobre un registro de recepción de arroz por parte de los supervisores.
    """
    _name = 'recepcion.arroz.log'
    _description = 'Historial de Modificaciones de Recepción'
    _order = 'create_date desc'

    recepcion_id = fields.Many2one(
        comodel_name='recepcion.arroz',
        string='Recepción Relacionada',
        required=True,
        ondelete='cascade',
        help='Registro de recepción al cual pertenece esta modificación.'
    )

    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Usuario que Modificó',
        default=lambda self: self.env.user,
        required=True,
        help='Usuario responsable de realizar la modificación.'
    )

    campo_modificado = fields.Char(
        string='Campo Modificado',
        required=True,
        help='Nombre técnico o descriptivo del campo alterado.'
    )

    valor_anterior = fields.Text(
        string='Valor Anterior',
        help='Representación en texto del valor previo a la modificación.'
    )

    valor_nuevo = fields.Text(
        string='Valor Nuevo',
        help='Representación en texto del nuevo valor asignado.'
    )

    motivo = fields.Text(
        string='Motivo de la Modificación',
        help='Explicación detallada del motivo de la alteración de datos.'
    )