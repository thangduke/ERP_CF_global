from odoo import models, fields, api
from odoo.exceptions import ValidationError, AccessError
import re

class GarmentConsumption(models.Model):
    _name = 'garment.consumption'
    _description = 'Consumption Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'

# region (Phần 2) liên kết
    style_id = fields.Many2one('garment.style', required=True)

    style_material_id = fields.Many2one(
        'garment.style.material',
        string='Material',
        required=True,
        domain="[('style_id', '=', style_id)]"
    )

    material_id = fields.Many2one(
        related='style_material_id.material_id',
        store=True,
        readonly=True
    )
# endregion
# region (Phần 3) Thông tin vật tư
    position = fields.Char(string='Position', related='material_id.position', store=True, readonly=True)
    
    mtr_no = fields.Char(string='Mtr#', related='material_id.mtr_no', store=True, readonly=True)
    
    mtr_code = fields.Char(string='Mtr Code', related='material_id.mtr_code', store=True, readonly=True)

    mtr_name = fields.Char(string='Mtr Name', related='material_id.mtr_name',store=True, readonly=True)
    
    mtr_type= fields.Char(string='Mtr Type', related='material_id.mtr_type.name',store=True, readonly=True)

    rate = fields.Char(string='Unit', related='material_id.rate',store=True,readonly=True)

    dimension = fields.Char(string='Dimension',related='material_id.dimension',store=True,readonly=True)

    supplier = fields.Many2one('supplier.partner',related='material_id.supplier',store=True,readonly=True)
    
# endregion
# region (Phần 1) THÔNG TIN CONSUMPTION LINE

    est_qty = fields.Float(string='Est.qty', required=True)
    
    fct_qty = fields.Float(string='Fct.qty',store=True)
    
    act_qty = fields.Float(string='Act.qty',store=True)
# endregion 
