from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ShelfList(models.Model):
    _name = 'shelf.list'
    _description = 'Danh sách kệ hàng'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "create_date desc"

    name = fields.Char(string="Tên kệ", required=True, tracking=True)
    store_id = fields.Many2one('store.list', string="Kho", required=True, ondelete='cascade', tracking=True)
    receive_id = fields.Many2one('material_receive', string="Đơn nhập hàng", tracking=True)
    shelf_line_ids= fields.One2many ('shelf.material.line','shelf_id', string="Vật tư trong kệ")
    grouped_line_ids = fields.One2many(
        'shelf.material.line.summary', 'shelf_id',
        string='Vật tư đã gộp',
        compute='_compute_grouped_line_ids',
        store=False
    )
    # Tạo trường tổng số lượng vật tư trong kệ
    def _compute_grouped_line_ids(self):
        for shelf in self:
            self.env['shelf.material.line.summary'].search([('shelf_id', '=', shelf.id)]).unlink()
            group_dict = {}
            for line in shelf.shelf_line_ids:
                key = (
                    line.position,
                    line.mtr_no,
                    line.mtr_type.id if line.mtr_type else False,
                    line.mtr_code,
                    line.mtr_name,
                    line.dimension,
                    line.color_item,
                    line.color_name,
                    line.color_set,
                    line.color_code,
                )
                if key not in group_dict:
                    group_dict[key] = {
                        'shelf_id': shelf.id,
                        'stock_id': line.stock_id.id if line.stock_id else False,
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
                        'est_qty': 0,
                        'act_qty': 0,
                        'rate': line.rate,
                        'supplier': line.supplier,
                        'country': line.country,
                    }
                group_dict[key]['est_qty'] += line.est_qty or 0
                group_dict[key]['act_qty'] += line.act_qty or 0
            for vals in group_dict.values():
                self.env['shelf.material.line.summary'].create(vals)
            shelf.grouped_line_ids = self.env['shelf.material.line.summary'].search([('shelf_id', '=', shelf.id)])
    
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

    
    def action_delete_selected_lines(self):
        for rec in self:
            lines_to_delete = rec.shelf_line_ids.filtered(lambda l: l.x_selected)
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
        """Export danh sách vật tư trong kệ"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/export/material/{self.id}',
            'target': 'self',
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