from odoo import models, fields, api

class GarmentColorcard(models.Model):
    _name = 'garment.colorcard'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Bảng màu sản phẩm'
    
# region (Phần 1) THÔNG TIN BẢNG MÀU SẢN PHẨM
    name = fields.Char(string="Tên bảng màu", required=True, tracking=True)

# endgion
# region (Phần 2) liên kết
    style_id = fields.Many2one('garment.style', string="Style", required=True)
    material_id = fields.Many2one('garment.material', string="Vật tư", required=True)
    colorway_id = fields.Many2one('garment.colorway', string="Màu sắc", required=True)
    
    material_color_id = fields.Many2one('material.color', string='Màu vật tư',store=True)
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