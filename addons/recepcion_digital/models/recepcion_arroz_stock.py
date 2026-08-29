# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

class RecepcionArrozStock(models.Model):
    """
    Extensión del modelo recepcion.arroz para encapsular los campos,
    relaciones y métodos de integración con el módulo de Inventario (Stock).
    """
    _inherit = 'recepcion.arroz'

    # --- INTEGRACIÓN CON INVENTARIO ---
    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Albarán de Inventario',
        readonly=True,
        copy=False,
        help='Documento de transferencia de inventario generado automáticamente al completar.'
    )

    lot_id = fields.Many2one(
        comodel_name='stock.lot',
        string='Lote de Almacén',
        readonly=True,
        copy=False,
        help='Número de lote de inventario asociado a esta recepción.'
    )

    def _create_stock_picking_and_lot(self):
        """
        Genera el lote de trazabilidad (stock.lot), la transferencia de inventario (stock.picking)
        y asigna las cantidades en peso acondicionado para su validación inmediata.
        """
        self.ensure_one()
        picking_obj = self.env['stock.picking']
        lot_obj = self.env['stock.lot']
        product_obj = self.env['product.product']

        # 1. Obtener o crear el producto "Arroz Paddy Verde"
        product = product_obj.search([('name', '=', 'Arroz Paddy Verde')], limit=1)
        if not product:
            product = product_obj.create({
                'name': 'Arroz Paddy Verde',
                'type': 'consu',
                'is_storable': True,
                'tracking': 'lot',
            })
        elif product.tracking == 'none':
            product.write({'tracking': 'lot'})

        # 2. Obtener el tipo de operación de recepción (Entradas)
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('warehouse_id.company_id', '=', self.env.company.id)
        ], limit=1)

        if not picking_type:
            raise UserError('No se encontró un tipo de operación de entrada (Incoming) configurado en el inventario.')

        # 3. Crear el Lote de Almacén
        lot = lot_obj.create({
            'name': self.name,
            'product_id': product.id,
            'company_id': self.env.company.id,
        })
        self.lot_id = lot.id

        # 4. Crear la Transferencia de Inventario
        location_supplier = self.partner_id.property_stock_supplier or self.env.ref('stock.stock_location_suppliers')
        location_dest = picking_type.default_location_dest_id

        picking = picking_obj.create({
            'partner_id': self.partner_id.id,
            'picking_type_id': picking_type.id,
            'location_id': location_supplier.id,
            'location_dest_id': location_dest.id,
            'origin': self.name,
            'move_ids': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': self.peso_acondicionado,
                'product_uom': product.uom_id.id,
                'location_id': location_supplier.id,
                'location_dest_id': location_dest.id,
            })],
        })

        # 5. Confirmar y asignar el lote a la línea de movimiento
        picking.action_confirm()
        picking.action_assign()

        for move_line in picking.move_line_ids:
            move_line.write({
                'lot_id': lot.id,
                'quantity': self.peso_acondicionado,
            })

        # 6. Validar la entrada a stock
        picking.button_validate()
        self.picking_id = picking.id
        return picking

    def action_view_picking(self):
        """
        Abre la vista formulario de la transferencia de inventario vinculada.
        """
        self.ensure_one()
        if not self.picking_id:
            raise UserError('No hay ninguna entrada de inventario generada para esta recepción.')
        return {
            'name': 'Entrada de Inventario',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }