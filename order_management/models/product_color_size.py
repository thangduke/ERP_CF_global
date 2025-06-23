from odoo import models, fields, api

class ProductColorSize(models.Model):
    _name = 'product.color.size'
    _description = 'Màu + Size trong mã hàng cụ thể'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "product_code_id, color_id, size_id"
    _rec_name = 'display_name'  # <-- thêm dòng này để chỉ định trường hiển thị

    display_name = fields.Char(string="Tên hiển thị", compute='_compute_display_name', store=True)

    @api.depends('product_code_id', 'color_id', 'size_id')
    def _compute_display_name(self):
        for rec in self:
            parts = [
                rec.product_code_id.name or '',
                rec.color_id.name or '',
                rec.size_id.name or ''
            ]
            rec.display_name = ' - '.join(filter(None, parts)) or 'Không xác định'
            
    product_code_id = fields.Many2one('product.code', string="Mã hàng", required=True, ondelete='cascade')
    warehouse_order_id = fields.Many2one('warehouse.order', string='Đơn hàng', help='Đơn hàng liên kết với biến thể này')
    
    material_ids = fields.One2many(
        'program.customer', 'color_size_id', 
        string="Danh sách vật tư", help="Vật tư định mức cho biến thể này"
    )   
    color_id = fields.Many2one('product.color', string="Màu", required=True)
    color = fields.Char(string="Mã màu", help="Mã màu của sản phẩm")
    @api.onchange('color_id')
    def _onchange_color_id(self):
        for rec in self:
            if rec.color_id:
                rec.color = rec.color_id.color_code or ''
            else:
                rec.color = ''
    size_id = fields.Many2one('product.size', string="Size", required=True)

    quantity = fields.Integer(string="Số lượng", default=0)
    
    aggregated_material_ids = fields.One2many(
        'warehouse.order.material.line.summary',
        'color_size_id',
        string='Vật tư tổng hợp',
        compute='_compute_grouped_material_line_ids',
        store=False,
        )
    def action_compute_grouped_materials(self):
        for record in self:
            record._compute_grouped_material_line_ids()
                  
    def _compute_grouped_material_line_ids(self):
        SummaryModel = self.env['warehouse.order.material.line.summary']
        for variant in self:
            # Xoá vật tư tổng cũ của chính biến thể này
            SummaryModel.search([('color_size_id', '=', variant.id)]).unlink()

            group_dict = {}
            qty = variant.quantity or 0
            for line in variant.material_ids:
                key = (
                    line.mtr_type.id if line.mtr_type else False,
                    line.mtr_name,
                    line.mtr_code,
                    line.mtr_no,
                    line.dimension,
                    line.color_item,
                    line.color_name,
                    line.color_set,
                    line.color_code,
                    line.rate,
                    line.supplier.id if line.supplier else False,
                )
                if key not in group_dict:
                    group_dict[key] = {
                        'color_size_id': variant.id,
                        'product_code_id': variant.product_code_id.id,
                        'position': line.position,
                        'mtr_no': line.mtr_no,
                        'mtr_type': line.mtr_type.id if line.mtr_type else False,
                        'mtr_code': line.mtr_code,
                        'mtr_name': line.mtr_name,
                        'dimension': line.dimension,
                        'color_item': line.color_item,
                        'color_name': line.color_name,
                        'color_set': line.color_set,
                        'color_code': line.color_code,
                        'rate': line.rate,
                        'price': line.price,
                        'supplier': line.supplier.id if line.supplier else False,
                        'country': line.country,
                        'est_qty': 0.0,
                        'act_qty': 0.0,
                    }
                group_dict[key]['est_qty'] += (line.est_qty or 0.0) * qty
                group_dict[key]['act_qty'] += (line.act_qty or 0.0) * qty

            # Tạo mới
            for vals in group_dict.values():
                SummaryModel.create(vals)

            # Gán kết quả
            variant.aggregated_material_ids = SummaryModel.search([
                ('color_size_id', '=', variant.id)
            ])
                       
    _sql_constraints = [
        ('unique_variant', 'unique(product_code_id, color_id, size_id)', 
         'Mỗi mã hàng chỉ được có một dòng cho mỗi Màu + Size.')
    ]
    
    # Thông tin người tạo
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)  
        return employee.id if employee else False
    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self._get_employee_default(), store=True)
    
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")
    
    date_create = fields.Datetime(string='Ngày tạo', default=fields.Datetime.now, readonly=True)
    
    
    label = fields.Char(string="Nhãn", help="Nhãn của sản phẩm")
    dimpk = fields.Float(string="DIMPK", help="Kích thước đóng gói")
    ppk = fields.Integer(string="PPK", help="Số lượng sản phẩm trong mỗi kiện")
    po_qty = fields.Integer(string="Số lượng PO", help="Số lượng đặt hàng")
    description = fields.Text(string='Mô tả', help="Mô tả sản phẩm", track_visibility='onchange')
    description_display = fields.Text('Mô tả', compute='_compute_description_display')   
    @api.depends('description')
    def _compute_description_display(self):
        for record in self:
            if record.description:
                record.description_display = record.description
            else:
                record.description_display = 'Không có mô tả'
    def action_delete_selected_lines(self):
        for rec in self:
            lines_to_delete = rec.material_ids.filtered(lambda l: l.x_selected)
            lines_to_delete.unlink()
            
    search_text = fields.Char(string='Search')
    search_active = fields.Boolean(string='Search Active', default=False)

    def action_search(self):
        """Kích hoạt tìm kiếm mà không làm mất dữ liệu gốc"""
        self.ensure_one()
        if not self.search_text:
            return

        self.search_active = True
        return {}

    def clear_search(self):
        """Xóa tìm kiếm và khôi phục danh sách ban đầu"""
        self.ensure_one()
        self.search_text = False
        self.search_active = False

        return {}

    @api.onchange('search_text')
    def _onchange_search_text(self):
        """Xóa tìm kiếm nếu người dùng xóa nội dung nhập"""
        if not self.search_text and self.search_active:
            self.clear_search()
            
    def button_dummy(self):
        """Empty method for dropdown toggle button"""
        return True
    
    def action_export(self):
        """Export thông tin khách hàng và định mức liên quan ra file Excel"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/export/product/{self.id}',
            'target': 'self',
        }
    
    def action_import(self):
        """Action to import materials for the current customer"""
        self.ensure_one()  # Đảm bảo chỉ có một bản ghi được chọn

        # Tạo wizard để tải file
        return { '''
            'type': 'ir.actions.act_window',
            'res_model': 'program.import.export.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_color_size_id': self.id,  # Truyền ID khách hàng vào wizard
            },'''
        }
    def open_product_color_size_form(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chi tiết màu & size',
            'res_model': 'product.color.size',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('order_management.view_product_color_size_form').id,
            'target': 'current',
            'flags': {'mode': 'edit'}
        }