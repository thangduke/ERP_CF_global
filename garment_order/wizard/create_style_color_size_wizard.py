from odoo import models, fields, api

class CreateStyleColorSizeWizard(models.TransientModel):
    _name = 'create.style.color.size.wizard'
    _description = 'Tạo style Màu - Size với số lượng'

    product_code_id = fields.Many2one('product.code', string="Style", required=True)
    customer_id = fields.Many2one('customer.cf', string="Khách hàng", related='product_code_id.customer_id', store=True)
    warehouse_order_id = fields.Many2one('warehouse.order', string="Chương trình", related='product_code_id.warehouse_order_id', store=True)

    color_ids = fields.Many2many('product.color', string="Danh sách Màu")
    size_ids = fields.Many2many('product.size', string="Danh sách Size")
    line_ids = fields.One2many('create.color.size.line', 'wizard_id', string="Chi tiết Màu - Size")

    def action_preview_lines(self):
        """Sinh danh sách tổ hợp màu-size"""
        self.ensure_one()
        self.line_ids.unlink()

        lines = []
        for color in self.color_ids:
            for size in self.size_ids:
                lines.append((0, 0, {
                    'color_id': color.id,
                    'size_id': size.id,
                    'selected': True,
                }))
        self.line_ids = lines

        return {
            'type': 'ir.actions.act_window',
            'name': 'Xác nhận tạo style',
            'res_model': 'create.style.color.size.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_create_color_size(self):
        """Tạo style"""
        ProductColorSize = self.env['product.color.size']
        created_count = 0

        for line in self.line_ids.filtered('selected'):
            exists = ProductColorSize.search([
                ('product_code_id', '=', self.product_code_id.id),
                ('color_id', '=', line.color_id.id),
                ('size_id', '=', line.size_id.id),
            ])
            if exists:
                continue
            ProductColorSize.create({
                'product_code_id': self.product_code_id.id,
                'color_id': line.color_id.id,
                'size_id': line.size_id.id,
                'order_qty': line.order_qty,
                'test_qty': line.test_qty,
                'unit_cost': line.unit_cost,
                'currency_id': line.currency_id.id,
            })
            created_count += 1

        message = f"✅ Đã tạo {created_count} style mới."
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Kết quả',
                'message': message,
                'sticky': False,
                'type': 'success'
            },
        }



class CreateColorSizeLine(models.TransientModel):
    _name = 'create.color.size.line'
    _description = 'Chi tiết tổ hợp Màu - Size trong Wizard'

    wizard_id = fields.Many2one('create.style.color.size.wizard', ondelete='cascade')
    selected = fields.Boolean(string="Chọn", default=True)
    color_id = fields.Many2one('product.color', string="Màu", required=True)
    color_code = fields.Char(string="Mã Màu", related='color_id.color_code', store=True)
    size_id = fields.Many2one('product.size', string="Size", required=True)
    order_qty = fields.Integer(string="Order.Qty")
    test_qty = fields.Integer(string="Test.Qty")
    currency_id = fields.Many2one(
        'res.currency',
        string='Tiền tệ',
        default=lambda self: self.env.ref('base.USD'),
        required=True,
        help="Tiền tệ sử dụng cho giá và số lượng")
    unit_cost = fields.Monetary(string="Đơn giá",help='Unit Cost', tracking=True,
        currency_field='currency_id', default=0)
    ext = fields.Monetary(string="Giá tổng",help='EXT', tracking=True,
        currency_field='currency_id',  default=0, compute='_compute_ext')
    
    @api.depends('order_qty', 'unit_cost')
    def _compute_ext(self):
        for rec in self:
            rec.ext = (rec.order_qty or 0.0) * (rec.unit_cost or 0.0) 

    
