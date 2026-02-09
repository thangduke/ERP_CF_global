from odoo import models, fields, api

class ShelfLevel(models.Model):
    _name = 'shelf.level'
    _description = 'Khoang trong kệ'

    name = fields.Char(string="Tên Khoang", required=True)
    
    code = fields.Char(string="Mã khoang", required=True)
    
    store_id = fields.Many2one('store.list', string="Kho", required=True,)
    shelf_id = fields.Many2one('shelf.list', string="Kệ", required=True, domain="[('store_id', '=', store_id)]")
    stock_summary_ids = fields.One2many(
        'material.stock.summary',
        'shelf_level_id',
        string="Vật tư trong khoang",
    )    
      
    capacity = fields.Float(string="Sức chứa (kg)")
    description = fields.Text(string="Mô tả")
    active = fields.Boolean(string="Active", default=True)
    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self._get_employee_default(), store=True)
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)
        return employee.id if employee else False

    date_create = fields.Datetime(string="Ngày tạo", default=fields.Datetime.now, readonly=True)
    def action_open_shelf_level(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Khoang trong kệ',
            'res_model': 'shelf.level',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',  # mở full màn hình
        }
    def action_delete_selected_lines(self):
        for rec in self:
            lines_to_delete = rec.stock_summary_ids.filtered(lambda l: l.x_selected)
            lines_to_delete.unlink()
            
    # region (Phần 1 tìm kiếm vật tư)        
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
    
    # endregion (Phần 1 tìm kiếm vật tư)
    
    def action_export(self):
        """Export danh sách vật tư trong kệ"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/export/material/{self.id}',
            'target': 'self',
        }
        


    