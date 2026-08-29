# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class RecepcionArroz(models.Model):
    _name = 'recepcion.arroz'
    _description = 'Registro de Recepcion de Arroz Paddy'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_recepcion desc, id desc'

    name = fields.Char(
        string='Folio de Recepción',
        required=True,
        copy=False,
        readonly=True,
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

    # --- VARIABLES DE LABORATORIO (%) ---
    porcentaje_humedad = fields.Float(
        string='Humedad (%)',
        digits=(5, 2),
        help='Porcentaje de humedad determinado en la muestra de laboratorio.'
    )

    porcentaje_impureza = fields.Float(
        string='Impurezas (%)',
        digits=(5, 2),
        help='Porcentaje de materias extrañas y vanos presentes en la muestra.'
    )

    porcentaje_grano_rojo = fields.Float(
        string='Grano Rojo (%)',
        digits=(5, 2),
        help='Porcentaje de presencia de grano rojo en la muestra analizada.'
    )

    # --- CÁLCULOS DE LIQUIDACIÓN Y DEDUCCIÓN (kg) ---
    descuento_humedad_kg = fields.Float(
        string='Descuento Humedad (kg)',
        compute='_compute_descuentos_laboratorio',
        store=True,
        digits=(16, 2),
        help='Kilos descontados calculados en función del exceso de humedad sobre la base estándar.'
    )

    descuento_impureza_kg = fields.Float(
        string='Descuento Impurezas (kg)',
        compute='_compute_descuentos_laboratorio',
        store=True,
        digits=(16, 2),
        help='Kilos descontados calculados en función del exceso de materias extrañas.'
    )

    peso_acondicionado = fields.Float(
        string='Peso Acondicionado (kg)',
        compute='_compute_descuentos_laboratorio',
        store=True,
        digits=(16, 2),
        help='Peso neto final aprovechable comercialmente tras aplicar deducciones técnicas.'
    )

    # --- ACCIONES Y TRANSICIONES DE ESTADO ---
    def action_completar(self):
        """
        Cambia el estado del registro a completado.
        """
        for record in self:
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

    # --- MÉTODOS COMPUTADOS Y REGLAS DE NEGOCIO ---
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

    @api.depends('peso_neto', 'porcentaje_humedad', 'porcentaje_impureza')
    def _compute_descuentos_laboratorio(self):
        """
        Calcula los kg a descontar por exceso de humedad e impurezas sobre la base estándar
        (Base Humedad Estándar: 12.0%, Base Impureza Estándar: 1.0%).
        Determina el peso acondicionado final del lote.
        """
        BASE_HUMEDAD = 12.0
        BASE_IMPUREZA = 1.0

        for record in self:
            if not record.peso_neto:
                record.descuento_humedad_kg = 0.0
                record.descuento_impureza_kg = 0.0
                record.peso_acondicionado = 0.0
                continue

            # Cálculo de deducción por exceso de humedad
            desc_hum = 0.0
            if record.porcentaje_humedad > BASE_HUMEDAD:
                exceso_humedad = record.porcentaje_humedad - BASE_HUMEDAD
                desc_hum = record.peso_neto * (exceso_humedad / 100.0)

            # Cálculo de deducción por exceso de impureza
            desc_imp = 0.0
            if record.porcentaje_impureza > BASE_IMPUREZA:
                exceso_impureza = record.porcentaje_impureza - BASE_IMPUREZA
                desc_imp = record.peso_neto * (exceso_impureza / 100.0)

            record.descuento_humedad_kg = desc_hum
            record.descuento_impureza_kg = desc_imp
            record.peso_acondicionado = record.peso_neto - (desc_hum + desc_imp)