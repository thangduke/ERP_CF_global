from odoo import models, fields, api
from odoo.exceptions import ValidationError

class StoreList(models.Model):
    _name = 'store.list'
    _description = 'Danh sách kho'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'
    _order = "create_date desc"

    name = fields.Char(string="Tên kho", required=True)
    # Liên kết model danh sách kho 
    shelf_ids = fields.One2many('shelf.list', 'store_id', string="Danh sách kệ hàng")
    shelf_level_ids = fields.One2many('shelf.level', 'store_id', string="Các khoang")
    
    stock_summary_ids = fields.One2many(
        'material.stock.summary',
        'store_id',
        string="Vật tư trong kho (chưa gán kệ)",)
    #    domain=[('shelf_id', '=', False)])
    # Trường để lưu mã kho hàng
    filtered_stock_summary_ids = fields.One2many(
        'material.stock.summary',
        'store_id',
        string="Vật tư chưa gán kệ",
        compute='_compute_filtered_lines',
        inverse='_inverse_filtered_lines',
        store=False
    )

    @api.depends('stock_summary_ids.shelf_id')
    def _compute_filtered_lines(self):
        for rec in self:
            rec.filtered_stock_summary_ids = rec.stock_summary_ids.filtered(lambda l: not l.shelf_id)

    def _inverse_filtered_lines(self):
        for rec in self:
            lines_with_shelf = rec.stock_summary_ids.filtered(lambda l: l.shelf_id)
            rec.stock_summary_ids = lines_with_shelf + rec.filtered_stock_summary_ids
            
    
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)
        return employee.id if employee else False
    
    image_128 = fields.Image("Image 128", max_width=128, max_height=128, store=True)
    
    employee_id = fields.Many2one(
        'employee.base', 'Người tạo',
        default=lambda self: self._get_employee_default(), store=True
    )
    
    store_index = fields.Char(string='Mã kho hàng')
    
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")

    date_create = fields.Datetime(string="Ngày tạo", default=fields.Datetime.now, readonly=True)

    active = fields.Boolean('Active', default=True)
    company= fields.Char(string='Công ty', help='Tên công ty mà kho hàng thuộc về')
    address = fields.Char(string='Địa chỉ')
    phone = fields.Char(string='Số điện thoại')
    description = fields.Text('Mô tả')
    description_display = fields.Text('Mô tả', compute='_compute_description_display')
    
    total_shelf = fields.Integer(
        string='Tổng số kệ', 
        compute='_compute_total_shelf',
        store=True,
    )

    @api.depends('shelf_ids')
    def _compute_total_shelf(self):
        for record in self:
            record.total_shelf = len(record.shelf_ids) 
    
    @api.depends('description')
    def _compute_description_display(self):
        for record in self:
            record.description_display = record.description or 'Không có mô tả'

    _sql_constraints = [
        ('unique_store_name', 'UNIQUE(name)', 'Tên kho đã tồn tại!')
    ]

    @api.constrains('name')
    def _check_unique_name(self):
        for record in self:
            if record.name:
                domain = [('name', '=', record.name), ('id', '!=', record.id)]
                if self.search_count(domain) > 0:
                    raise ValidationError('Tên kho "%s" đã tồn tại!' % record.name)
                
                
    # region (phần 2) : Bộ lọc tìm kiếm 
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
    
    
    # endregion
    
    def action_export(self):
        """Export danh sách vật tư trong kệ"""
        self.ensure_one()
        return {}
    
    def action_assign_location(self):
        """Mở wizard gán kệ cho vật tư"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Gán kệ cho vật tư',
            'res_model': 'assign.shelf.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_store_id': self.id,
            }
        }
        
    def action_create_shelf(self):
        """
        Mở form view để tạo một kệ mới, với kho mặc định là kho hiện tại.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tạo kệ mới',
            'res_model': 'shelf.list',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_store_id': self.id,
            }
        }