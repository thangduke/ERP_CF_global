from odoo import models, fields, api

class MaterialReceive(models.Model):
    _name = 'material.receive'
    _description = 'Vật tư - Nhập kho'

    receipt_no = fields.Char(string="Mã nhập kho", readonly=True, copy=False,)
    # Tự động cập nhật mã nhập kho khi tạo mới        
    @api.model
    def default_get(self, fields_list):
        """Gán giá trị mặc định cho receipt_no khi mở form view"""
        defaults = super(MaterialReceive, self).default_get(fields_list)
        if 'receipt_no' in fields_list:
            defaults['receipt_no'] = self.env['ir.sequence'].next_by_code('material.receive') or 'New'
        return defaults

    # Tạo số tự động khi tạo mới
    customer_id = fields.Many2one('customer.cf', string="Khách hàng")
    
    store_id = fields.Many2one('store.list', string="Kho")
    shelf_id = fields.Many2one(
        'shelf.list',
        string="Kệ hàng",
        domain="[('store_id', '=', store_id)]"
    )
    invoice_id = fields.Many2one('material.purchase.order', string="Mã ivoice ", required=True)
    
    # Gán dòng vật tư liên quan
    material_line_ids = fields.One2many('material.line', compute='_compute_preview_lines', string="Xem trước vật tư", store=False)
    
    @api.onchange('invoice_id')
    def _compute_preview_lines(self):
        for rec in self:
            rec.material_line_ids = rec.invoice_id.line_ids
            
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)  
        return employee.id if employee else False

    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self._get_employee_default(), store=True)
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")
    date_create = fields.Datetime(string='Ngày tạo', default=fields.Datetime.now, readonly=True)
    purpose = fields.Char(string="Mục đích nhập kho")

    def action_delete_selected_lines(self):
        for rec in self:
            lines_to_delete = rec.material_line_ids.filtered(lambda l: l.x_selected)
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
        """Export danh sách vật tư trong đơn nhập kho"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/export/material_receive/{self.id}',
            'target': 'self',
        }
        
    @api.model
    def create(self, vals):
        record = super().create(vals)
        # Lấy các dòng vật tư từ invoice
        material_lines = record.invoice_id.line_ids
        shelf_material_line_obj = self.env['shelf.material.line']
        for line in material_lines:
            shelf_material_line_obj.create({
                'receive_id': record.id,
                'stock_id': record.store_id.id,
                'shelf_id': record.shelf_id.id,
          #      'employee_id': record.employee_id.id,
                'entry_date': fields.Date.today(),
                'position': line.position,
                'mtr_no': line.mtr_no,
                'mtr_type': line.mtr_type.id,
                'mtr_code': line.mtr_code,
                'mtr_name': line.mtr_name,
                'dimension': line.dimension,
                'color_item': line.color_item,
                'color_name': line.color_name,
                'color_set': line.color_set,
                'color_code': line.color_code,
                'est_qty': line.est_qty,
                'act_qty': line.act_qty,
                'rate': line.rate,
                'supplier': line.supplier,
                'country': line.country,
            })
        return record
