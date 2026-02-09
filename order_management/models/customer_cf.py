# models/customer.py
from odoo import models, fields , api, _
from odoo.exceptions import UserError, ValidationError

class CustomerCf(models.Model):
    _name = 'customer.cf'
    _description = 'Khách hàng'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'
    _order = "create_date desc"
    _rec_name = 'display_name'
    
    name_customer = fields.Char(string='Tên khách hàng', required=True, tracking=True)
    customer_index = fields.Char(string='Mã khách hàng', copy=False, readonly=True, )    
    @api.model
    def create(self, vals):
        if vals.get('customer_index', _('New')) == _('New'):
            vals['customer_index'] = self.env['ir.sequence'].next_by_code('customer.cf') or _('New')
        return super(CustomerCf, self).create(vals)
    
    phone = fields.Char(string='Số điện thoại')
    
    display_name = fields.Char(string='Tên hiển thị', compute='_compute_display_name', store=True)
    @api.depends('name_customer', 'customer_index')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.customer_index} - {record.name_customer}"

    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self._get_employee_default(), store=True)
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)  
        return employee.id if employee else False    
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")
    date_create = fields.Datetime(string='Ngày tạo', default=fields.Datetime.now, readonly=True)

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
                
    _sql_constraints = [
        ('name_customer_unique', 'unique(name_customer)', 'Tên khách hàng đã tồn tại!')
    ]