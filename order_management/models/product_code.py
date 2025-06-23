from odoo import models, fields, api

class ProductCode(models.Model):
    _name = 'product.code'
    _description = 'Mã hàng'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "create_date desc"

    # Thông tin cơ bản
    name = fields.Char(string="Mã hàng", required=True, track_visibility='onchange')
    warehouse_order_id = fields.Many2one('warehouse.order', string="Đơn hàng", ondelete='cascade')
    color_size_ids = fields.One2many('product.color.size', 'product_code_id', 
        string="Danh sách Màu + Size")
    
    # Thông tin người tạo
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)  
        return employee.id if employee else False
    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self._get_employee_default(), store=True)
    
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")
    date_create = fields.Datetime(string='Ngày tạo', default=fields.Datetime.now, readonly=True)
    x_selected = fields.Boolean(string="Chọn")   
    
    description_display = fields.Text('Mô tả', compute='_compute_description_display')
    active = fields.Boolean(string='Kích hoạt', default=True)
    description = fields.Text(string='Mô tả', help="Mô tả sản phẩm", track_visibility='onchange')

    @api.depends('description')
    def _compute_description_display(self):
        for record in self:
            if record.description:
                record.description_display = record.description
            else:
                record.description_display = 'Không có mô tả'
                
    def action_delete_selected_lines(self):
        for rec in self:
            lines_to_delete = rec.color_size_ids.filtered(lambda l: l.x_selected)
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
        #    'type': 'ir.actions.act_url',
        #    'url': f'/export/product/{self.id}',
        #   'target': 'self',
        }
    
    def action_import(self):
        """Action to import materials for the current customer"""
        self.ensure_one()  # Đảm bảo chỉ có một bản ghi được chọn

        # Tạo wizard để tải file
        return {
        '''    'type': 'ir.actions.act_window',
            'res_model': 'program.import.export.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_progarm_customer_id': self.id,  # Truyền ID khách hàng vào wizard
            },'''
        }
                  
    # Danh sách vật tư tổng hợp theo mã hàng
    aggregated_material_ids = fields.One2many(
        'warehouse.order.material.line.summary',
        'product_code_id',
        string='Vật tư tổng hợp',
        compute='_compute_grouped_material_line_ids',
        store=False,
    )
    def action_compute_grouped_materials(self):
        for record in self:
            record._compute_grouped_material_line_ids()
            
    def _compute_grouped_material_line_ids(self):
        SummaryModel = self.env['warehouse.order.material.line.summary']
        for product in self:
            # Xóa vật tư tổng cũ theo mã hàng
            SummaryModel.search([('product_code_id', '=', product.id)]).unlink()

            group_dict = {}

            # Gộp vật tư từ từng biến thể (color + size)
            for variant in product.color_size_ids:
                # Đảm bảo mỗi variant đã có vật tư tổng trước khi lấy
                variant._compute_grouped_material_line_ids()

                for line in variant.aggregated_material_ids:
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
                            'product_code_id': product.id,
                            'order_id': product.warehouse_order_id.id if product.warehouse_order_id else False,
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

                    group_dict[key]['est_qty'] += line.est_qty or 0.0
                    group_dict[key]['act_qty'] += line.act_qty or 0.0

            # Tạo dữ liệu tổng hợp mới
            for vals in group_dict.values():
                SummaryModel.create(vals)

            # Gán kết quả vào field One2many
            product.aggregated_material_ids = SummaryModel.search([
                ('product_code_id', '=', product.id)
            ])

    def open_product_code_form(self):
        """Mở form view mã hàng product.code theo id"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chi tiết Mã hàng',
            'res_model': 'product.code',
            'res_id':  self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('order_management.view_product_code_form').id,
            'target': 'current',
            'flags': {'mode': 'edit'}
        }