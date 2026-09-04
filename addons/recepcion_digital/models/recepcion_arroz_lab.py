# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class RecepcionArrozLab(models.Model):
    """
    Extensión del modelo recepcion.arroz para encapsular los campos,
    cálculos matemáticos y validaciones asociadas al análisis de laboratorio.
    """
    _inherit = 'recepcion.arroz'

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

    # --- MÉTODOS COMPUTADOS Y REGLAS DE NEGOCIO ---
    @api.depends('peso_neto', 'porcentaje_humedad', 'porcentaje_impureza')
    def _compute_descuentos_laboratorio(self):
        """
        Calcula los kilos a descontar por exceso de humedad e impurezas sobre la base estándar
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
            record.peso_acondicionado = max(0.0, record.peso_neto - (desc_hum + desc_imp))

    # --- RESTRICCIONES DE INTEGRIDAD Y VALIDACIONES ---
    @api.constrains('porcentaje_humedad', 'porcentaje_impureza', 'porcentaje_grano_rojo')
    def _check_porcentajes_laboratorio(self):
        """
        Valida que los porcentajes ingresados en laboratorio se encuentren en el rango de 0 a 100.
        """
        for record in self:
            if not (0.0 <= record.porcentaje_humedad <= 100.0):
                raise ValidationError('El porcentaje de humedad debe estar comprendido entre 0% y 100%.')
            if not (0.0 <= record.porcentaje_impureza <= 100.0):
                raise ValidationError('El porcentaje de impurezas debe estar comprendido entre 0% y 100%.')
            if not (0.0 <= record.porcentaje_grano_rojo <= 100.0):
                raise ValidationError('El porcentaje de grano rojo debe estar comprendido entre 0% y 100%.')