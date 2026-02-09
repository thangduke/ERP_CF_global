from odoo import models, fields, api

class SupplierGarment(models.Model):
    _name = 'supplier.garment'
    _description = 'Nhà cung cấp'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name_supplier'

    name_supplier = fields.Char(string='Tên nhà cung cấp', required=True, tracking=True)
    supplier_index = fields.Char(string='Mã NCC')
    address = fields.Char(string='Địa chỉ')
    phone = fields.Char(string='Số điện thoại')
    email = fields.Char(string='Email')
    website = fields.Char(string='Website')
    country_id = fields.Many2one('res.country', string='Quốc gia', ondelete='restrict')
    city = fields.Char(string='Thành phố')
    
    active = fields.Boolean(string='Kích hoạt', default=True)
    # Thông tin người tạo
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)  
        return employee.id if employee else False
    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self._get_employee_default(), store=True)
    
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")
    
    date_create = fields.Datetime(string='Ngày tạo', default=fields.Datetime.now, readonly=True)
    
    _sql_constraints = [
        ('name_supplier_unique', 'unique(name_supplier)', 'Tên nhà cung cấp đã tồn tại!'),
        ('supplier_index_unique', 'unique(supplier_index)', 'Mã NCC đã tồn tại!')
    ]