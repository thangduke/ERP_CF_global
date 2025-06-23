# models/customer.py
from odoo import models, fields , api, _
from odoo.exceptions import UserError, ValidationError

class CustomerCf(models.Model):
    _name = 'customer.cf'
    _description = 'Khách hàng'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'
    _order = "create_date desc"
    
    name = fields.Char(string='Tên khách hàng', required=True)
    phone = fields.Char(string='Số điện thoại')
    
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)  
        return employee.id if employee else False
    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self._get_employee_default(), store=True)
    
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")
    date_create = fields.Datetime(string='Ngày tạo', default=fields.Datetime.now, readonly=True)
    customer_index = fields.Char(string='Mã khách hàng')
    
    email = fields.Char(string='Email')
    address = fields.Text(string='Địa chỉ')
    
    description = fields.Text(string='Mô tả chi tiết về khách hàng')
    description_display = fields.Text('Mô tả', compute='_compute_description_display')
    active = fields.Boolean(string='Kích hoạt', default=True)

    @api.depends('description')
    def _compute_description_display(self):
        for record in self:
            if record.description:
                record.description_display = record.description
            else:
                record.description_display = 'Không có mô tả'
                
