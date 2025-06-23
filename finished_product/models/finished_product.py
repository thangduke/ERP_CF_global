from odoo import models, fields

class FinishedProduct(models.Model):
    _name = 'finished.product'
    _description = 'Kho Thành Phẩm'

    name = fields.Char('Tên thành phẩm', required=True)
    product_code = fields.Char('Mã thành phẩm')
    category = fields.Selection([
        ('shirt', 'Áo'),
        ('pants', 'Quần'),
        ('dress', 'Đầm'),
    ], string='Loại sản phẩm')
    color = fields.Char('Màu sắc')
    size = fields.Char('Kích thước')
    unit = fields.Char('Đơn vị tính')
    quantity = fields.Float('Số lượng')
    completed_date = fields.Date('Ngày hoàn thành')
    location = fields.Char('Vị trí kho')
    design_id = fields.Many2one('design.library', string='Thiết kế liên quan')
    description = fields.Text('Mô tả')