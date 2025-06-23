from odoo import models, fields, api

class MaterialPurchaseOrder(models.Model):
    _name = 'material.purchase.order'
    _description = 'PO vật tư theo nhà cung cấp từ đơn hàng'

    name = fields.Char(string='Số PO', required=True, copy=False, default='New')
    # Tự động cập nhật mã PO       
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            # Gọi sequence đã khai báo trong XML
            vals['name'] = self.env['ir.sequence'].next_by_code('material.purchase.order') or '/'
        return super(MaterialPurchaseOrder, self).create(vals)
    
    order_id = fields.Many2one('warehouse.order', string='Đơn hàng nguồn', required=True)
    
    supplier_id = fields.Many2one('supplier.partner', string='Nhà cung cấp', required=True)
    
    date_order = fields.Date(string='Ngày tạo đơn', default=fields.Date.today)
    note = fields.Text(string='Ghi chú')

    line_ids = fields.One2many('material.line', 'po_id', string='Chi tiết vật tư')

    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)  
        return employee.id if employee else False
    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self._get_employee_default(), store=True)
    
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")
    
    date_create = fields.Datetime(string='Ngày tạo', default=fields.Datetime.now, readonly=True)
  
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
    def open_po_form_view(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'PO vật tư',
            'res_model': 'material.purchase.order',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('order_management.material_purchase_order_form_view').id,
            'target': 'current',
            'flags': {'mode': 'edit'}
        }