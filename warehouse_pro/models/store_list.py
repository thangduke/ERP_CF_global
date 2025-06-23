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
    # Liên kết model danh sách vật tư trong kho
    grouped_line_ids = fields.One2many(
        'shelf.material.line.summary', 'stock_id',
        string='Vật tư đã gộp theo kho',
        compute='_compute_grouped_line_ids',
        store=False
    )

    def _compute_grouped_line_ids(self):
        for store in self:
            self.env['shelf.material.line.summary'].search([('stock_id', '=', store.id)]).unlink()
            group_dict = {}
            # Lấy tất cả vật tư trong các kệ thuộc kho này
            all_lines = self.env['shelf.material.line'].search([('stock_id', '=', store.id)])
            for line in all_lines:
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
                        'stock_id': store.id,
                        'mtr_no': line.mtr_no,
                        'position': line.position,
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
            store.grouped_line_ids = self.env['shelf.material.line.summary'].search([('stock_id', '=', store.id)])
              
    
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")

    date_create = fields.Datetime(string="Ngày tạo", default=fields.Datetime.now, readonly=True)

    active = fields.Boolean('Active', default=True)
    address = fields.Text(string='Địa chỉ')
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
    
    def action_export(self):
        """Export danh sách vật tư trong kệ"""
        self.ensure_one()
        return {}