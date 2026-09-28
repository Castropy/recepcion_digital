# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class RecepcionController(http.Controller):
    """
    Controlador API REST/JSON-RPC para la integración con la aplicación móvil Recepción Digital (React Native).
    Provee endpoints escalables para autenticación, sincronización por etapas y acceso a catálogos.
    """

    @http.route('/api/recepcion/login', type='json', auth='none', methods=['POST'], csrf=False)
    def api_login(self, **kwargs):
        """
        Endpoint de autenticación para usuarios de la aplicación móvil.
        Soporta inicio de sesión mediante Cédula de Identidad (hr.employee) o Correo/Login (res.users).
        """
        # Desempaquetado dinámico de parámetros JSON-RPC
        data = request.dispatcher.jsonrequest or {}
        params = data.get('params', data) if isinstance(data, dict) else {}

        login_input = params.get('login') or kwargs.get('login')
        password = params.get('password') or kwargs.get('password')
        db_name = params.get('db') or request.db or (http.db_monitored()[0] if http.db_monitored() else None)

        if not login_input or not password:
            return {'status': 'error', 'message': 'Credenciales incompletas.'}

        login_usuario = str(login_input).strip()

        try:
            # 1. Búsqueda por Cédula en Empleados (hr.employee)
            if hasattr(request.env, 'hr.employee'):
                empleado = request.env['hr.employee'].sudo().search([
                    ('identification_id', '=', login_usuario)
                ], limit=1)

                if empleado and empleado.user_id:
                    login_usuario = empleado.user_id.login

            # 2. Autenticación oficial e inequívoca de Odoo
            uid = request.session.authenticate(db_name, login_usuario, password)

            if uid:
                user = request.env['res.users'].browse(uid)
                
                # Mapear área de trabajo asignada o fallback
                role = getattr(user, 'area_trabajo', None) or 'romana'

                _logger.info("Usuario %s (UID: %s) autenticado exitosamente con rol: %s", user.login, uid, role)

                return {
                    'status': 'success',
                    'uid': uid,
                    'name': user.name,
                    'login': user.login,
                    'role': role,
                    'session_id': request.session.sid,
                }
        except Exception as error:
            _logger.error("Error durante el proceso de autenticación: %s", str(error))
            return {'status': 'error', 'message': f"Error de autenticación: {str(error)}"}

        return {'status': 'error', 'message': 'Credenciales inválidas.'}

    @http.route('/api/recepcion/sincronizar', type='json', auth='user', methods=['POST'], csrf=False)
    def api_sincronizar(self, **kwargs):
        """
        Endpoint de sincronización para procesar o actualizar registros
        de recepción enviados desde la cola offline de React Native.
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
            _logger.error("Error al sincronizar lote local_id %s: %s", local_id, str(error))
            return {
                'status': 'error',
                'local_id': local_id,
                'message': str(error)
            }

    @http.route('/api/recepcion/crear', type='jsonrpc', auth='user', methods=['POST'], csrf=False)
    def crear_recepcion(self, **kwargs):
        """
        Endpoint para creación directa de lotes de inventario.
        """
        data = request.dispatcher.jsonrequest or {}
        params = data.get('params', data) if isinstance(data, dict) else {}

        lot = request.env['stock.lot'].sudo().create({
            'name':          params.get('lote_nombre'),
            'product_id':    params.get('product_id'),
            'company_id':    request.env.company.id,
            'variedad':      params.get('variedad'),
            'peso_bruto':    params.get('peso_bruto'),
            'tara_camion':   params.get('tara_camion'),
            'humedad':       params.get('humedad'),
            'impurezas':     params.get('impurezas'),
            'placa_camion':  params.get('placa'),
            'nombre_chofer': params.get('chofer'),
            'silo_asignado': params.get('silo'),
        })

        return {
            'success': True,
            'lot_id':   lot.id,
            'lot_name': lot.name,
            'estado_calidad': getattr(lot, 'estado_calidad', 'borrador'),
            'peso_neto': getattr(lot, 'peso_neto', 0.0),
        }

    @http.route('/api/recepcion/proveedores', type='jsonrpc', auth='user', methods=['POST'], csrf=False)
    def listar_proveedores(self, **kwargs):
        """
        Endpoint para listar el catálogo de proveedores activos.
        """
        proveedores = request.env['res.partner'].sudo().search([
            ('supplier_rank', '>', 0)
        ])
        return [{
            'id':     p.id,
            'nombre': p.name,
            'rif':    p.vat,
        } for p in proveedores]