# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # --- RELACIÓN CON RECEPCIONES ---
    recepcion_arroz_ids = fields.One2many(
        comodel_name='recepcion.arroz',
        inverse_name='partner_id',
        string='Recepciones de Arroz',
        help='Historial completo de entregas de materia prima registradas para este proveedor.'
    )

    recepcion_count = fields.Integer(
        string='Nro. de Recepciones',
        compute='_compute_recepcion_stats',
        help='Cantidad total de recepciones registradas a nombre del proveedor.'
    )

    total_peso_acondicionado_kg = fields.Float(
        string='Total Acondicionado (kg)',
        compute='_compute_recepcion_stats',
        digits=(16, 2),
        help='Suma acumulada del peso acondicionado en kilogramos entregado por el proveedor.'
    )

    # --- MÉTODOS COMPUTADOS Y NAVEGACIÓN ---
    @api.depends('recepcion_arroz_ids', 'recepcion_arroz_ids.peso_acondicionado', 'recepcion_arroz_ids.state')
    def _compute_recepcion_stats(self):
        """
        Calcula el total de recepciones asociadas y la suma del peso acondicionado en kg.
        Excluye los registros en estado cancelado.
        """
        for partner in self:
            recepciones_validas = partner.recepcion_arroz_ids.filtered(lambda r: r.state != 'cancelado')
            partner.recepcion_count = len(recepciones_validas)
            partner.total_peso_acondicionado_kg = sum(recepciones_validas.mapped('peso_acondicionado'))

    def action_view_recepciones_arroz(self):
        """
        Retorna una accion de ventana para desplegar la lista filtrada de recepciones del proveedor.
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("recepcion_digital.action_recepcion_arroz")
        action['domain'] = [('partner_id', '=', self.id)]
        action['context'] = {'default_partner_id': self.id}
        return action