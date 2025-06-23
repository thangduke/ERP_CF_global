# models/design_library.py
from odoo import models, fields

class DesignLibrary(models.Model):
    _name = 'design.library'
    _description = 'Thư Viện Thiết Kế'

    name = fields.Char('Tên thiết kế', required=True)
    design_code = fields.Char('Mã thiết kế')
    designer_id = fields.Many2one('res.users', string='Người thiết kế')
    product_type = fields.Selection([
        ('shirt', 'Áo'),
        ('pants', 'Quần'),
        ('dress', 'Đầm')
    ], string='Loại sản phẩm')
    size_range = fields.Char('Khoảng size')
    color_palette = fields.Char('Bảng màu')
    design_file = fields.Binary('Tệp thiết kế')
    description = fields.Text('Mô tả')