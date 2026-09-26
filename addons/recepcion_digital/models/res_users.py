# -*- coding: utf-8 -*-
from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    area_trabajo = fields.Selection(
        selection=[
            ('romana', 'Romana / Báscula'),
            ('laboratorio', 'Laboratorio de Calidad'),
            ('supervision', 'Supervisión / Planta'),
            ('administracion', 'Administración'),
        ],
        string='Área de Trabajo',
        default='romana',
        help='Área de trabajo del colaborador.'
    )

    def get_user_app_profile(self):
        """
        Método helper diseñado para ser invocado desde la API REST/JSON-RPC en React Native.
        Retorna el perfil del usuario autenticado, su área y sus roles asignados.
        """
        self.ensure_one()

        # Identificar el rol principal según los grupos de seguridad
        role = 'user'
        if self.has_group('recepcion_digital.group_recepcion_manager'):
            role = 'manager'
        elif self.has_group('recepcion_digital.group_recepcion_laboratorio'):
            role = 'laboratorio'
        elif self.has_group('recepcion_digital.group_recepcion_romana'):
            role = 'romana'

        # Resguardo en caso de que hr (employee_id) no esté instalado o asignado
        employee = getattr(self, 'employee_id', False)
        employee_id = employee.id if employee else False
        employee_name = employee.name if employee else self.name

        return {
            'user_id': self.id,
            'name': self.name,
            'login': self.login,
            'employee_id': employee_id,
            'employee_name': employee_name,
            'area_trabajo': self.area_trabajo or 'romana',
            'role': role,
            'groups': [group.xml_id for group in self.groups_id if group.xml_id],
        }