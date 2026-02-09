from odoo import models, fields, api
from odoo.exceptions import ValidationError, AccessError
import re

class GarmentMaterial(models.Model):
    _name = 'garment.material'
    _description = 'Danh sách vật tư'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'
    _rec_name = 'mtr_no'
    
# region (Phần 1) THÔNG TIN VẬT TƯ
    position = fields.Char(string='Position')
    name_en = fields.Char(string ='Tên English', )
    
    name_vi = fields.Char(string ='Tên tiếng việt', tracking=True)
    
    mtr_no = fields.Char(string="Mtr#", help='Mã code định mức', compute='_compute_name', readonly=True,  store=True)  
    
    mtr_code = fields.Char(string='Mtr Code', help='Code item của nhà cung cấp', required=True) 

    mtr_name = fields.Char(string="Mtr Name", help="Tên vật tư")  # Tên vật tư / Mtr Name
    
    mtr_type = fields.Many2one('material.type', string="Mtr Type", help="Loại vật tư")
    
    image_128 = fields.Image("Image 128", max_width=128, max_height=128, store=True)    
    
    rate = fields.Char(string="Unit", related='rate_id.name', store=True, help='Ví dụ: mét, cuộn, cái...')
    rate_id = fields.Many2one('material.rate', string="Unit", required=True, help='Ví dụ: mét, cuộn, cái...')
    
    # * Dimension theo vật tư, Size
    dimension = fields.Char(string="Dimension", related='dimension_id.name', store=True, help="Kích thước theo ngữ cảnh")
    dimension_id = fields.Many2one('material.dimension', string="Dimension", help="Kích thước theo ngữ cảnh")
    
    # * Chọn NCC theo vật tư        
    supplier = fields.Many2one('supplier.partner', string="Supplier", help="Nhà cung cấp vật tư")
    supplier_index = fields.Char(string="Supplier#", help="Mã số nhà cung cấp", related='supplier.supplier_index', store=True)
    
    # Mô tả vật tư / Description
    description = fields.Char(string='Mô tả', help="Mô tả vật tư")
    
# endregion

# region (Phần 2) liên kết
    color_id = fields.One2many('material.color', 'material_id', string='Màu sắc vật tư', help='Danh sách màu sắc của vật tư')
    
    consumption_line_ids = fields.One2many('garment.consumption', 'material_id', string='Consumption Lines', help='Danh sách định mức tiêu hao vật tư')
    
    
# endregion


# region (Phần 4) rate
class MaterialDimention(models.Model):
    _name = 'garment.dimention'
    _description = 'Dimention'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'
    
    name = fields.Char(string='Dimension', required=True, tracking=True)
    
# endregion


    