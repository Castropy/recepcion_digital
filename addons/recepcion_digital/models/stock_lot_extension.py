from odoo import models, fields, api
from odoo.exceptions import ValidationError

class StockLot(models.Model):
    _inherit = 'stock.lot'

    # Datos de campo
    variedad = fields.Char('Variedad', help='Ej: Araure 4, Cimarrón, Fonaiap 1')
    
    # Pesaje
    peso_bruto = fields.Float('Peso bruto (kg)', digits=(10, 2))
    tara_camion = fields.Float('Tara camión (kg)', digits=(10, 2))
    peso_neto = fields.Float(
        'Peso neto (kg)', compute='_compute_peso_neto',
        store=True, digits=(10, 2)
    )

    # Calidad
    humedad = fields.Float('Humedad (%)', digits=(5, 2))
    impurezas = fields.Float('Impurezas (%)', digits=(5, 2))
    estado_calidad = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('aprobado',  'Aprobado'),
        ('revision',  'En revisión'),
        ('rechazado', 'Rechazado'),
    ], default='pendiente', string='Estado calidad')

    # Evidencias
    foto_recepcion = fields.Binary('Foto del grano')
    foto_filename  = fields.Char('Nombre foto')
    firma_chofer   = fields.Binary('Firma del chofer')

    # Metadatos
    placa_camion    = fields.Char('Placa camión')
    nombre_chofer   = fields.Char('Nombre chofer')
    silo_asignado   = fields.Char('Silo asignado')

    # Umbrales (configurables por empresa)
    HUMEDAD_MAX = 14.0
    IMPUREZAS_MAX = 2.0

    @api.depends('peso_bruto', 'tara_camion')
    def _compute_peso_neto(self):
        for rec in self:
            rec.peso_neto = max(rec.peso_bruto - rec.tara_camion, 0.0)

    @api.constrains('humedad')
    def _check_humedad(self):
        for rec in self:
            if rec.humedad and rec.humedad > self.HUMEDAD_MAX:
                rec.estado_calidad = 'revision'
                # Aquí irá la notificación al jefe de planta