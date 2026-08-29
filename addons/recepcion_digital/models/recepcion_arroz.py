# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

class RecepcionArroz(models.Model):
    """
    Modelo principal para la gestión y registro del proceso de recepción de Arroz Paddy.
    Actúa como orquestador del flujo operativo y consolida la información general.
    """
    _name = 'recepcion.arroz'
    _description = 'Registro de Recepción de Arroz Paddy'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_recepcion desc, id desc'

    # --- IDENTIFICACIÓN Y ESTADOS ---
    name = fields.Char(
        string='Folio de Recepción',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('recepcion.arroz') or 'NUEVO',
        help='Secuencia única generada para el ticket de recepción.'
    )
    
    state = fields.Selection(
        selection=[
            ('borrador', 'Borrador'),
            ('pesaje_inicial', 'Pesaje Inicial'),
            ('laboratorio', 'Laboratorio'),
            ('pesaje_final', 'Pesaje Final'),
            ('completado', 'Completado'),
            ('cancelado', 'Cancelado'),
        ],
        string='Estado',
        default='borrador',
        tracking=True,
        required=True,
        help='Indica la etapa operativa en la que se encuentra la recepción.'
    )

    date_recepcion = fields.Datetime(
        string='Fecha y Hora de Entrada',
        default=fields.Datetime.now,
        required=True,
        help='Fecha y hora en que el vehículo ingresa a la planta.'
    )

    # --- DATOS DE ORIGEN Y TRAZABILIDAD ---
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Productor / Proveedor',
        required=True,
        domain="[('is_company', '=', True)]",
        help='Entidad o productor agrícola que entrega la materia prima.'
    )

    guia_sica = fields.Char(
        string='Nro. Guía SICA / INSAI',
        required=True,
        help='Número de documento de movilización emitido por los entes gubernamentales.'
    )

    chofer_nombre = fields.Char(
        string='Nombre del Conductor',
        required=True,
        help='Nombre y apellido de la persona que transporta la carga.'
    )

    chofer_cedula = fields.Char(
        string='Cédula del Conductor',
        required=True,
        help='Documento de identidad del conductor del vehículo.'
    )

    vehiculo_placa = fields.Char(
        string='Placa del Vehículo',
        required=True,
        help='Matrícula del camión o gandola de transporte.'
    )

    variedad_arroz = fields.Selection(
        selection=[
            ('fl_supa', 'FL-Supa'),
            ('md_248', 'MD-248'),
            ('cimarron', 'Cimarrón'),
            ('otra', 'Otra Variedad'),
        ],
        string='Variedad del Arroz',
        required=True,
        default='fl_supa',
        help='Variedad genética de la materia prima recibida.'
    )

    # --- PESAJE DE BÁSCULA (kg) ---
    peso_bruto = fields.Float(
        string='Peso Bruto (kg)',
        digits=(16, 2),
        help='Peso total registrado en báscula al ingresar el vehículo lleno.'
    )

    peso_tara = fields.Float(
        string='Peso Tara (kg)',
        digits=(16, 2),
        help='Peso del vehículo vacío registrado al salir de la tolva.'
    )

    peso_neto = fields.Float(
        string='Peso Neto (kg)',
        compute='_compute_peso_neto',
        store=True,
        digits=(16, 2),
        help='Diferencia calculada entre el Peso Bruto y la Tara.'
    )

    # --- ACCIONES Y ORQUESTACIÓN DE ESTADOS ---
    def action_completar(self):
        """
        Orquesta la finalización de la recepción.
        Valida el peso acondicionado y delega la creación de inventario a su submódulo.
        """
        for record in self:
            if record.peso_acondicionado <= 0:
                raise UserError('No se puede completar una recepción con peso acondicionado menor o igual a 0 kg.')

            # Delegación al submódulo de inventario
            record._create_stock_picking_and_lot()
            
            record.state = 'completado'

    def action_draft(self):
        """
        Regresa el registro al estado borrador.
        """
        for record in self:
            record.state = 'borrador'

    def action_cancelar(self):
        """
        Cancela la recepción de arroz.
        """
        for record in self:
            record.state = 'cancelado'

    # --- MÉTODOS COMPUTADOS BASE ---
    @api.depends('name', 'partner_id', 'guia_sica')
    def _compute_display_name(self):
        """
        Calcula la representación en texto del registro para búsquedas y vistas relacionales.
        """
        for record in self:
            proveedor = record.partner_id.name if record.partner_id else 'Sin Proveedor'
            guia = f" ({record.guia_sica})" if record.guia_sica else ''
            record.display_name = f"{record.name} - {proveedor}{guia}"

    @api.depends('peso_bruto', 'peso_tara')
    def _compute_peso_neto(self):
        """
        Calcula el peso neto del vehículo.
        Retorna la diferencia positiva entre peso bruto y tara.
        """
        for record in self:
            if record.peso_bruto and record.peso_tara:
                if record.peso_tara >= record.peso_bruto:
                    raise ValidationError('El peso tara no puede ser mayor o igual al peso bruto.')
                record.peso_neto = record.peso_bruto - record.peso_tara
            else:
                record.peso_neto = 0.0

    # --- RESTRICCIONES DE INTEGRIDAD BASE ---
    @api.constrains('peso_bruto', 'peso_tara')
    def _check_pesos_positivos(self):
        """
        Valida que los pesos registrados no sean valores negativos.
        """
        for record in self:
            if record.peso_bruto < 0.0:
                raise ValidationError('El peso bruto no puede ser un valor negativo.')
            if record.peso_tara < 0.0:
                raise ValidationError('El peso tara no puede ser un valor negativo.')