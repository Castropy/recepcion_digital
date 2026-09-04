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

    # --- PROMEDIOS DE CALIDAD Y LABORATORIO ---
    promedio_humedad = fields.Float(
        string='Humedad Promedio (%)',
        compute='_compute_recepcion_stats',
        digits=(5, 2),
        help='Promedio del porcentaje de humedad en las cargas entregadas por el proveedor.'
    )

    promedio_impureza = fields.Float(
        string='Impureza Promedio (%)',
        compute='_compute_recepcion_stats',
        digits=(5, 2),
        help='Promedio del porcentaje de impurezas presentes en los envíos del proveedor.'
    )

    promedio_grano_rojo = fields.Float(
        string='Grano Rojo Promedio (%)',
        compute='_compute_recepcion_stats',
        digits=(5, 2),
        help='Promedio del porcentaje de grano rojo determinado en laboratorio.'
    )

    # --- MÉTODOS COMPUTADOS Y NAVEGACIÓN ---
    @api.depends(
        'recepcion_arroz_ids', 
        'recepcion_arroz_ids.peso_acondicionado', 
        'recepcion_arroz_ids.porcentaje_humedad',
        'recepcion_arroz_ids.porcentaje_impureza',
        'recepcion_arroz_ids.porcentaje_grano_rojo',
        'recepcion_arroz_ids.state'
    )
    def _compute_recepcion_stats(self):
        """
        Calcula el total de recepciones, peso acumulado y promedios de variables de laboratorio.
        Excluye los registros en estado cancelado.
        """
        for partner in self:
            recepciones_validas = partner.recepcion_arroz_ids.filtered(lambda r: r.state != 'cancelado')
            count = len(recepciones_validas)
            partner.recepcion_count = count
            partner.total_peso_acondicionado_kg = sum(recepciones_validas.mapped('peso_acondicionado'))

            if count > 0:
                partner.promedio_humedad = sum(recepciones_validas.mapped('porcentaje_humedad')) / count
                partner.promedio_impureza = sum(recepciones_validas.mapped('porcentaje_impureza')) / count
                partner.promedio_grano_rojo = sum(recepciones_validas.mapped('porcentaje_grano_rojo')) / count
            else:
                partner.promedio_humedad = 0.0
                partner.promedio_impureza = 0.0
                partner.promedio_grano_rojo = 0.0

    def action_view_recepciones_arroz(self):
        """
        Retorna una acción de ventana para desplegar la lista filtrada de recepciones del proveedor.
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("recepcion_digital.action_recepcion_arroz")
        action['domain'] = [('partner_id', '=', self.id)]
        action['context'] = {'default_partner_id': self.id}
        return action