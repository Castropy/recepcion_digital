# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    area_trabajo = fields.Selection(
        related='employee_id.area_trabajo',
        string='Área de Trabajo',
        readonly=True,
        store=True,
        help='Área de trabajo del colaborador enlazado.'
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

        return {
            'user_id': self.id,
            'name': self.name,
            'login': self.login,
            'employee_id': self.employee_id.id or False,
            'employee_name': self.employee_id.name or self.name,
            'area_trabajo': self.area_trabajo or 'romana',
            'role': role,
            'groups': [group.xml_id for group in self.groups_id if group.xml_id],
        }