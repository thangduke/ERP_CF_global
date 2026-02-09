from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ShelfList(models.Model):
    _name = 'shelf.list'
    _description = 'Danh sách kệ hàng'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "create_date desc"

    name = fields.Char(string="Tên kệ", required=True, tracking=True)
    store_id = fields.Many2one('store.list', string="Kho", required=True, ondelete='cascade', tracking=True)

    level_ids = fields.One2many('shelf.level', 'shelf_id', string="Các khoang")   
    
    receive_id = fields.Many2one('material_receive', string="Đơn nhập hàng", tracking=True)

    stock_summary_ids = fields.One2many(
        'material.stock.summary',
        'shelf_id',
        string="Vật tư trong kệ",
    )
     
    total_shelf = fields.Integer(
        string='Tổng số kệ', 
        compute='_compute_total_shelf_level',
        store=True,
    )

    @api.depends('level_ids')
    def _compute_total_shelf_level(self):
        for record in self:
            record.total_shelf = len(record.level_ids) 
    
    # Tự động gán nhân viên tạo kệ
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)  
        return employee.id if employee else False
    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self._get_employee_default(), store=True)  
    code = fields.Char(string="Mã kệ", required=True, tracking=True)
    capacity = fields.Float(string="Sức chứa (kg)", tracking=True)
    
    description = fields.Text(string="Mô tả")
    
    active = fields.Boolean(string="Active", default=True)
    date_create = fields.Datetime(string="Ngày tạo", default=fields.Datetime.now, readonly=True)
    # Danh sách vật tư trong kệ 
    def action_open_shelf_list(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Kệ hàng',
            'res_model': 'shelf.list',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',  # mở full màn hình
        }
    
    def action_delete_selected_lines(self):
        for rec in self:
            lines_to_delete = rec.stock_summary_ids.filtered(lambda l: l.x_selected)
            lines_to_delete.unlink()
            
    # region (phần) Tìm kiếm vật tư trong kệ
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
    
    # endregion
    
    def action_export(self):
        """Export danh sách vật tư trong kệ"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/export/material/{self.id}',
            'target': 'self',
        }
    
    def action_create_level(self):
        """
        Mở form view để tạo một khoang mới, với kệ mặc định là kệ hiện tại.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tạo khoang mới',
            'res_model': 'shelf.level',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_shelf_id': self.id,
                'default_store_id': self.store_id.id,
            }
        }    
    
    '''
    _sql_constraints = [
        ('unique_shelf_code', 'UNIQUE(code, store_id)', 'Mã kệ đã tồn tại trong kho này!')
    ]

    @api.constrains('code')
    def _check_unique_code(self):
        for record in self:
            if record.code:
                domain = [('code', '=', record.code), ('store_id', '=', record.store_id.id), ('id', '!=', record.id)]
                if self.search_count(domain) > 0:
                    raise ValidationError('Mã kệ "%s" đã tồn tại trong kho "%s"!' % (record.code, record.store_id.name))
    '''