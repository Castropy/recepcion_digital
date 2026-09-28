# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class RecepcionController(http.Controller):
    """
    Controlador API REST para la integracion con la aplicacion movil React Native.
    Provee endpoints para autenticacion, sincronizacion por etapas y catalogos.
    """

    @http.route('/api/recepcion/login', type='json', auth='none', methods=['POST'], csrf=False)
    def api_login(self, **kwargs):
        """
        Endpoint de autenticacion para usuarios de la aplicacion movil.
        Soporta autenticacion por Cedula de Identidad (hr.employee) o Correo (res.users).
        """
        # Extraer parametros recibidos via JSON-RPC
        data = request.dispatcher.jsonrequest or {}
        params = data.get('params', data) if isinstance(data, dict) else {}

        login_input = params.get('login') or kwargs.get('login')
        password = params.get('password') or kwargs.get('password')
        db = params.get('db') or request.db or (http.db_monitored()[0] if http.db_monitored() else None)

        if not login_input or not password:
            return {'status': 'error', 'message': 'Credenciales incompletas.'}

        login_usuario = login_input.strip()

        try:
            # 1. Intentar buscar si el login introducido corresponde a la Cedula (identification_id) de un empleado
            empleado = request.env['hr.employee'].sudo().search([
                ('identification_id', '=', login_usuario)
            ], limit=1)

            if empleado and empleado.user_id:
                login_usuario = empleado.user_id.login

            # 2. Autenticar la sesion contra Odoo
            uid = request.session.authenticate(db, login_usuario, password)
            if uid:
                user = request.env['res.users'].browse(uid)
                
                # Obtener el rol / area de trabajo asignada al usuario
                role = 'romana'
                if hasattr(user, 'area_trabajo') and user.area_trabajo:
                    role = user.area_trabajo

                return {
                    'status': 'success',
                    'uid': uid,
                    'name': user.name,
                    'login': user.login,
                    'role': role,
                    'session_id': request.session.sid,
                }
        except Exception as error:
            return {'status': 'error', 'message': str(error)}

        return {'status': 'error', 'message': 'Credenciales invalidas.'}

    @http.route('/api/recepcion/sincronizar', type='json', auth='user', methods=['POST'], csrf=False)
    def api_sincronizar(self, **kwargs):
        """
        Endpoint de sincronizacion para procesar o actualizar registros
        de recepcion enviados desde la cola offline de React Native.
        """
        data = request.dispatcher.jsonrequest or {}
        params = data.get('params', data) if isinstance(data, dict) else {}

        local_id = params.get('local_id')
        odoo_id = params.get('id')
        valores = params.get('valores', {})

        recepcion_obj = request.env['recepcion.arroz']

        try:
            if odoo_id:
                record = recepcion_obj.browse(odoo_id)
                if record.exists():
                    record.write(valores)
                    return {
                        'status': 'success',
                        'local_id': local_id,
                        'id': record.id,
                        'name': record.name,
                        'state': record.state,
                    }

            nuevo_registro = recepcion_obj.create(valores)
            return {
                'status': 'success',
                'local_id': local_id,
                'id': nuevo_registro.id,
                'name': nuevo_registro.name,
                'state': nuevo_registro.state,
            }

        except Exception as error:
            return {
                'status': 'error',
                'local_id': local_id,
                'message': str(error)
            }

    @http.route('/api/recepcion/crear', type='jsonrpc', auth='user', methods=['POST'], csrf=False)
    def crear_recepcion(self, **kwargs):
        """
        Endpoint legacy para creacion directa de lotes de inventario.
        """
        data = request.jsonrequest
        
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
            'lot_id':   lot.id,
            'lot_name': lot.name,
            'estado_calidad': lot.estado_calidad,
            'peso_neto': lot.peso_neto,
        }

    @http.route('/api/recepcion/proveedores', type='jsonrpc', auth='user', methods=['POST'], csrf=False)
    def listar_proveedores(self, **kwargs):
        """
        Endpoint para listar el catalogo de proveedores activos.
        """
        proveedores = request.env['res.partner'].sudo().search([
            ('supplier_rank', '>', 0)
        ])
        return [{
            'id':     p.id,
            'nombre': p.name,
            'rif':    p.vat,
        } for p in proveedores]