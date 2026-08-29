# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

class RecepcionArrozPurchase(models.Model):
    """
    Extensión del modelo recepcion.arroz para gestionar la integración 
    con el módulo de Compras de Odoo (purchase.order).
    """
    _inherit = 'recepcion.arroz'

    # --- INTEGRACIÓN CON COMPRAS ---
    purchase_id = fields.Many2one(
        comodel_name='purchase.order',
        string='Orden de Compra',
        readonly=True,
        copy=False,
        help='Orden de compra generada automáticamente al completar la recepción.'
    )

    def _create_purchase_order(self, product):
        """
        Genera una Orden de Compra en estado borrador basada en los kilos 
        acondicionados y el proveedor de la recepción actual.
        """
        self.ensure_one()
        purchase_obj = self.env['purchase.order']

        purchase = purchase_obj.create({
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'name': f'Arroz Paddy Acondicionado - Folio {self.name}',
                'product_qty': self.peso_acondicionado,
                'product_uom': product.uom_id.id,
                'price_unit': 0.0,
                'date_planned': fields.Datetime.now(),
            })],
        })
        self.purchase_id = purchase.id
        return purchase

    def action_view_purchase(self):
        """
        Abre la vista formulario de la Orden de Compra vinculada a esta recepción.
        """
        self.ensure_one()
        if not self.purchase_id:
            raise UserError('No hay ninguna orden de compra generada para esta recepción.')
        return {
            'name': 'Orden de Compra',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': self.purchase_id.id,
            'view_mode': 'form',
            'target': 'current',
        }