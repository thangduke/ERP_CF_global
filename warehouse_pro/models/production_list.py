from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ProductionList(models.Model):
    _name = 'production.list'
    _description = 'Danh sách dây chuyền'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'avatar.mixin', 'image.mixin']
    _mail_post_access = 'read'
    _order = "create_date desc"

    name = fields.Char(string="Tên dây chuyền", required=True)

    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)
        return employee.id if employee else False

    employee_id = fields.Many2one(
        'employee.base', 'Người tạo',
        default=lambda self: self._get_employee_default(), store=True
    )
    production_index = fields.Char(string='Mã dây chuyền')
    
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")

    date_create = fields.Datetime(string="Ngày tạo", default=fields.Datetime.now, readonly=True)

    active = fields.Boolean('Active', default=True)
    description = fields.Text('Mô tả')
    address = fields.Text(string='Địa chỉ')
    phone = fields.Char(string='Số điện thoại')
    description_display = fields.Text('Mô tả', compute='_compute_description_display')

    @api.depends('description')
    def _compute_description_display(self):
        for record in self:
            record.description_display = record.description or 'Không có mô tả'

    _sql_constraints = [
        ('unique_production_name', 'UNIQUE(name)', 'Tên dây chuyền đã tồn tại!')
    ]

    @api.constrains('name')
    def _check_unique_name(self):
        for record in self:
            if record.name:
                domain = [('name', '=', record.name), ('id', '!=', record.id)]
                if self.search_count(domain) > 0:
                    raise ValidationError('Tên dây chuyền "%s" đã tồn tại!' % record.name)
