# -*- coding: utf-8 -*-
import logging

import odoo
from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)


class RecepcionController(http.Controller):
    """
    Controlador API REST/JSON-RPC para la integración con la aplicación
    móvil Recepción Digital (React Native).

    Compatible con Odoo 19.
    """

    @http.route(
        '/api/recepcion/login',
        type='json',
        auth='none',
        methods=['POST'],
        csrf=False,
    )
    def api_login(self, **kwargs):
        """
        Endpoint de autenticación para usuarios de la aplicación móvil.

        Permite iniciar sesión mediante:
        - Cédula/DNI del empleado (hr.employee.identification_id).
        - Login/correo electrónico de res.users.
        """

        data = request.dispatcher.jsonrequest or {}
        params = data.get('params', data) if isinstance(data, dict) else {}

        login_input = params.get('login') or kwargs.get('login')
        password = params.get('password') or kwargs.get('password')
        db_name = params.get('db') or request.db

        if not login_input or not password:
            return {
                'status': 'error',
                'message': 'Credenciales incompletas.',
            }

        if not db_name:
            return {
                'status': 'error',
                'message': 'No se pudo determinar la base de datos.',
            }

        login_usuario = str(login_input).strip()

        try:
            # Odoo 19 requiere un Environment para session.authenticate().
            # Si la petición ya tiene la BD solicitada, se reutiliza su env.
            # En caso contrario, se crea un cursor/env para la BD indicada,
            # siguiendo el mismo patrón utilizado por el controlador oficial
            # de /web/session/authenticate.
            if request.db == db_name:
                env = request.env
                auth_info = self._authenticate_user(
                    env,
                    login_usuario,
                    password,
                )
            else:
                with odoo.modules.registry.Registry(db_name).cursor() as cr:
                    env = odoo.api.Environment(cr, None, {})
                    auth_info = self._authenticate_user(
                        env,
                        login_usuario,
                        password,
                    )

                    return self._build_login_response(
                        env,
                        auth_info,
                        db_name,
                    )

            # En este caso request.db ya coincide con db_name y la sesión
            # puede guardarse directamente.
            return self._build_login_response(
                env,
                auth_info,
                db_name,
            )

        except Exception as error:
            _logger.exception(
                "Error durante el proceso de autenticación para el usuario %s",
                login_usuario,
            )

            return {
                'status': 'error',
                'message': f'Error de autenticación: {str(error)}',
            }

    @staticmethod
    def _authenticate_user(env, login_usuario, password):
        """
        Resuelve el DNI a un login de Odoo y autentica las credenciales.

        Odoo 19 recibe el Environment como primer argumento de
        request.session.authenticate(), no el nombre de la base de datos.
        """

        # ==============================================================
        # 1. BÚSQUEDA POR DNI EN hr.employee
        # ==============================================================

        try:
            empleado = env['hr.employee'].sudo().search(
                [
                    ('identification_id', '=', login_usuario),
                ],
                limit=1,
            )

            if empleado and empleado.user_id:
                login_usuario = empleado.user_id.login

        except Exception:
            # Si hr.employee no está disponible o la búsqueda falla,
            # se continúa intentando autenticar el valor introducido
            # como login/correo electrónico.
            _logger.exception(
                "No se pudo buscar el empleado por DNI: %s",
                login_usuario,
            )

        # ==============================================================
        # 2. CREDENCIALES PARA ODOO 19
        # ==============================================================

        credential = {
            'login': login_usuario,
            'password': password,
            'type': 'password',
        }

        # IMPORTANTE:
        # En Odoo 19 el primer argumento es el Environment.
        auth_info = request.session.authenticate(env, credential)

        return auth_info

    @staticmethod
    def _build_login_response(env, auth_info, db_name):
        """
        Guarda la sesión autenticada y construye la respuesta del login.
        """

        if not isinstance(auth_info, dict):
            return {
                'status': 'error',
                'message': 'Respuesta de autenticación inválida.',
            }

        uid = auth_info.get('uid')

        if not uid:
            return {
                'status': 'error',
                'message': 'Credenciales inválidas.',
            }

        # Guarda la base de datos en la sesión y persiste la sesión.
        # Este es el mismo mecanismo utilizado por Odoo 19 en su
        # controlador oficial de autenticación.
        request.session.db = db_name
        request._save_session(env)

        user = env['res.users'].sudo().browse(uid)

        if not user.exists():
            return {
                'status': 'error',
                'message': 'Usuario autenticado pero no encontrado.',
            }

        role = getattr(user, 'area_trabajo', False) or 'romana'

        _logger.info(
            "Usuario %s (UID: %s) autenticado exitosamente "
            "en Odoo 19 con rol: %s",
            user.login,
            uid,
            role,
        )

        return {
            'status': 'success',
            'uid': uid,
            'name': user.name,
            'login': user.login,
            'role': role,
            'session_id': request.session.sid,
        }

    @http.route(
        '/api/recepcion/sincronizar',
        type='json',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
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
            _logger.error(
                "Error al sincronizar lote local_id %s: %s",
                local_id,
                str(error),
            )

            return {
                'status': 'error',
                'local_id': local_id,
                'message': str(error),
            }

    @http.route(
        '/api/recepcion/crear',
        type='jsonrpc',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def crear_recepcion(self, **kwargs):
        """
        Endpoint para creación directa de lotes de inventario.
        """

        data = request.dispatcher.jsonrequest or {}
        params = data.get('params', data) if isinstance(data, dict) else {}

        lot = request.env['stock.lot'].sudo().create({
            'name': params.get('lote_nombre'),
            'product_id': params.get('product_id'),
            'company_id': request.env.company.id,
            'variedad': params.get('variedad'),
            'peso_bruto': params.get('peso_bruto'),
            'tara_camion': params.get('tara_camion'),
            'humedad': params.get('humedad'),
            'impurezas': params.get('impurezas'),
            'placa_camion': params.get('placa'),
            'nombre_chofer': params.get('chofer'),
            'silo_asignado': params.get('silo'),
        })

        return {
            'success': True,
            'lot_id': lot.id,
            'lot_name': lot.name,
            'estado_calidad': getattr(
                lot,
                'estado_calidad',
                'borrador',
            ),
            'peso_neto': getattr(lot, 'peso_neto', 0.0),
        }

    @http.route(
        '/api/recepcion/proveedores',
        type='jsonrpc',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def listar_proveedores(self, **kwargs):
        """
        Endpoint para listar el catálogo de proveedores activos.
        """

        proveedores = request.env['res.partner'].sudo().search([
            ('supplier_rank', '>', 0),
        ])

        return [
            {
                'id': p.id,
                'nombre': p.name,
                'rif': p.vat,
            }
            for p in proveedores
        ]
