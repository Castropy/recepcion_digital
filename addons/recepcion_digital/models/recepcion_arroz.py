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

    # --- AUDITORÍA DE COLABORADORES Y OPERADORES ---
    usuario_romana_id = fields.Many2one(
        comodel_name='res.users',
        string='Operador de Romana',
        default=lambda self: self.env.user,
        help='Usuario que registró el pesaje del vehículo.'
    )

    operador_id = fields.Many2one(
        related='usuario_romana_id',
        string='Operador de Báscula',
        store=True,
        readonly=False,
        help='Alias relacional para operador de báscula en la vista.'
    )

    usuario_laboratorio_id = fields.Many2one(
        comodel_name='res.users',
        string='Analista de Laboratorio',
        help='Usuario que ingresó los datos de análisis de calidad.'
    )

    analista_id = fields.Many2one(
        related='usuario_laboratorio_id',
        string='Analista de Laboratorio',
        store=True,
        readonly=False,
        help='Alias relacional para analista de laboratorio en la vista.'
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

    # --- ANÁLISIS DE LABORATORIO Y LIQUIDACIÓN ---
    porcentaje_humedad = fields.Float(string='% Humedad', digits=(5, 2))
    porcentaje_impureza = fields.Float(string='% Impureza', digits=(5, 2))
    porcentaje_grano_rojo = fields.Float(string='% Grano Rojo', digits=(5, 2))

    descuento_humedad_kg = fields.Float(string='Descuento Humedad (kg)', compute='_compute_liquidacion', store=True)
    descuento_impureza_kg = fields.Float(string='Descuento Impureza (kg)', compute='_compute_liquidacion', store=True)
    peso_acondicionado = fields.Float(string='Peso Acondicionado (kg)', compute='_compute_liquidacion', store=True)

    # --- INTEGRACIÓN CON INVENTARIO Y COMPRAS ---
    picking_id = fields.Many2one('stock.picking', string='Entrada de Almacén', readonly=True)
    purchase_id = fields.Many2one('purchase.order', string='Orden de Compra', readonly=True)
    lot_id = fields.Many2one('stock.lot', string='Lote de Almacén', readonly=True)

    # --- AUDITORÍA DE CAMBIOS ---
    log_ids = fields.One2many(
        comodel_name='recepcion.arroz.log',
        inverse_name='recepcion_id',
        string='Historial de Modificaciones',
        help='Muestra los registros de auditoria sobre los cambios de datos en la recepcion.'
    )

    # --- MÉTODOS ORM (CREACIÓN, EDICIÓN Y GESTIÓN) ---
    @api.model_create_multi
    def create(self, vals_list):
        """
        Sobrescribe el método create para permitir la creación automática 
        de un nuevo proveedor en res.partner si se ingresa texto libre en partner_id.
        """
        new_vals_list = []
        for vals in vals_list:
            vals_dict = dict(vals)
            partner_val = vals_dict.get('partner_id')
            if partner_val and isinstance(partner_val, str):
                partner = self.env['res.partner'].create({
                    'name': partner_val,
                    'is_company': True,
                })
                vals_dict['partner_id'] = partner.id
            new_vals_list.append(vals_dict)
        return super(RecepcionArroz, self).create(new_vals_list)

    def write(self, vals):
        """
        Sobrescribe el método write para interceptar modificaciones en campos críticos
        y generar logs de auditoría de forma automática.
        """
        campos_auditables = {
            'peso_bruto': 'Peso Bruto',
            'peso_tara': 'Peso Tara',
            'porcentaje_humedad': 'Porcentaje Humedad',
            'porcentaje_impureza': 'Porcentaje Impureza',
            'porcentaje_grano_rojo': 'Porcentaje Grano Rojo',
            'partner_id': 'Productor / Proveedor',
            'guia_sica': 'Guía SICA',
            'vehiculo_placa': 'Placa Vehículo'
        }

        for record in self:
            logs_a_crear = []
            for campo_tecnico, etiqueta in campos_auditables.items():
                if campo_tecnico in vals:
                    valor_previo = str(getattr(record, campo_tecnico) or '')
                    valor_nuevo = str(vals[campo_tecnico] or '')
                    if valor_previo != valor_nuevo:
                        logs_a_crear.append({
                            'recepcion_id': record.id,
                            'campo_modificado': etiqueta,
                            'valor_anterior': valor_previo,
                            'valor_nuevo': valor_nuevo,
                            'motivo': vals.get('motivo_modificacion', 'Modificación registrada desde la app o interfaz Odoo')
                        })
            if logs_a_crear:
                self.env['recepcion.arroz.log'].create(logs_a_crear)

        return super(RecepcionArroz, self).write(vals)

    # --- ACCIONES Y SMART BUTTONS ---
    def action_view_picking(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_purchase(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': self.purchase_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_completar(self):
        """
        Orquesta la finalización de la recepción.
        Valida el peso, delega la creación de inventario (picking/lote)
        y genera automáticamente la Orden de Compra asociada.
        """
        for record in self:
            peso_final = record.peso_acondicionado or record.peso_neto
            if peso_final <= 0:
                raise UserError('No se puede completar una recepción con peso menor o igual a 0 kg.')

            picking = False
            if hasattr(record, '_create_stock_picking_and_lot'):
                picking = record._create_stock_picking_and_lot()

            if picking and getattr(picking, 'move_ids', False):
                product = picking.move_ids[0].product_id
                if hasattr(record, '_create_purchase_order'):
                    record._create_purchase_order(product)

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

    @api.depends('peso_neto', 'porcentaje_humedad', 'porcentaje_impureza')
    def _compute_liquidacion(self):
        """
        Calcula las deducciones de humedad e impurezas sobre el peso neto.
        """
        for record in self:
            exc_humedad = max(0.0, record.porcentaje_humedad - 12.0)
            exc_impureza = max(0.0, record.porcentaje_impureza - 2.0)

            desc_h = record.peso_neto * (exc_humedad / 100.0)
            desc_i = record.peso_neto * (exc_impureza / 100.0)

            record.descuento_humedad_kg = desc_h
            record.descuento_impureza_kg = desc_i
            record.peso_acondicionado = max(0.0, record.peso_neto - desc_h - desc_i)

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