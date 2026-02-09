from odoo import models, fields, api
from odoo.exceptions import ValidationError, AccessError
import re

class GarmentMaterialQuotation(models.Model):
    _name = 'garment.material.quotation'
    _description = 'Material Quotation'

    style_material_id = fields.Many2one(
        'garment.style.material',
        required=True
    )

    material_id = fields.Many2one(
        related='style_material_id.material_id',
        store=True
    )

    supplier_id = fields.Many2one('supplier_garment', string="Supplier")

    cif_price = fields.Float()
    fob_price = fields.Float()
    exwork_price = fields.Float()
    buying_price = fields.Float()

    currency_id = fields.Many2one('res.currency')
    min_order_qty = fields.Float()
