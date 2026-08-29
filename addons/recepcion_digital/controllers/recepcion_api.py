from odoo import http
from odoo.http import request


class RecepcionController(http.Controller):

    @http.route('/api/recepcion/crear', type='jsonrpc',
                auth='user', methods=['POST'], csrf=False)
    def crear_recepcion(self, **kwargs):
        data = request.jsonrequest
        
        # Buscar o crear el lote
        lot = request.env['stock.lot'].sudo().create({
            'name':          data.get('lote_nombre'),
            'product_id':    data.get('product_id'),
            'company_id':    request.env.company.id,
            'variedad':      data.get('variedad'),
            'peso_bruto':    data.get('peso_bruto'),
            'tara_camion':   data.get('tara_camion'),
            'humedad':       data.get('humedad'),
            'impurezas':     data.get('impurezas'),
            'placa_camion':  data.get('placa'),
            'nombre_chofer': data.get('chofer'),
            'silo_asignado': data.get('silo'),
        })

        return {
            'success': True,
            'lot_id':  lot.id,
            'lot_name': lot.name,
            'estado_calidad': lot.estado_calidad,
            'peso_neto': lot.peso_neto,
        }

    @http.route('/api/recepcion/proveedores', type='jsonrpc',
                auth='user', methods=['POST'], csrf=False)
    def listar_proveedores(self, **kwargs):
        proveedores = request.env['res.partner'].sudo().search([
            ('supplier_rank', '>', 0)
        ])
        return [{
            'id':     p.id,
            'nombre': p.name,
            'rif':    p.vat,
        } for p in proveedores]