from odoo import models, fields, api

class Supplier(models.Model):
    _name = 'supplier.partner'
    _description = 'Nhà cung cấp'

    name = fields.Char(string='Tên nhà cung cấp', required=True)
    code = fields.Char(string='Mã NCC')
    address = fields.Char(string='Địa chỉ')
    phone = fields.Char(string='Số điện thoại')
    email = fields.Char(string='Email')
    website = fields.Char(string='Website')
    country_id = fields.Many2one('res.country', string='Quốc gia', ondelete='restrict')
    city = fields.Char(string='Thành phố')
    
    active = fields.Boolean(string='Kích hoạt', default=True)
    color = fields.Integer (string="Màu sắc",)
    
    # Thông tin người tạo
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)  
        return employee.id if employee else False
    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self._get_employee_default(), store=True)
    
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")
    
    date_create = fields.Datetime(string='Ngày tạo', default=fields.Datetime.now, readonly=True)