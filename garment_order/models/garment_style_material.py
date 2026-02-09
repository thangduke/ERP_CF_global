from odoo import models, fields, api
from odoo.exceptions import ValidationError, AccessError
import re

class GarmentStyleMaterial(models.Model):
    _name = 'garment.style.material'
    _description = 'Material Master theo Style'

# region (Phần 2) liên kết với Style và Material
    style_id = fields.Many2one(
        'garment.style',
        required=True,
        ondelete='cascade'
    )

    material_id = fields.Many2one(
        'garment.material',
        required=True
    )
    consumption_id = fields.One2many(
        'garment.consumption',
        'style_material_id'
    )

    quotation_ids = fields.One2many(
        'garment.material.quotation',
        'style_material_id'
    )   
# endregion
# region (Phần 1) THÔNG TIN VẬT TƯ
    position = fields.Char(string='Position', related='material_id.position', store=True, readonly=True)
    
    mtr_no = fields.Char(string='Mtr#', related='material_id.mtr_no', store=True, readonly=True)
    
    mtr_code = fields.Char(string='Mtr Code', related='material_id.mtr_code', store=True, readonly=True)

    mtr_name = fields.Char(string='Mtr Name', related='material_id.mtr_name',store=True, readonly=True)
    
    mtr_type= fields.Char(string='Mtr Type', related='material_id.mtr_type.name',store=True, readonly=True)

    rate = fields.Char(string='Unit', related='material_id.rate',store=True,readonly=True)

    dimension = fields.Char(string='Dimension',related='material_id.dimension',store=True,readonly=True)

    supplier = fields.Many2one('supplier.partner',related='material_id.supplier',store=True,readonly=True)

    _sql_constraints = [
        ('uniq_style_material',
         'unique(style_id, material_id)',
         'Mỗi vật tư chỉ được khai báo 1 lần cho mỗi Style')
    ]
# endregion