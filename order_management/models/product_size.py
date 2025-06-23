from odoo import models, fields, api

class ProductSize(models.Model):
    _name = 'product.size'
    _description = 'Kích thước sản phẩm'

    name = fields.Char ( string="Size", required=True)
    active = fields.Boolean(string='Kích hoạt', default=True)
    color = fields.Integer (string="Màu sắc")
    
    # Thông tin người tạo
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)  
        return employee.id if employee else False
    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self._get_employee_default(), store=True)
    
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")
    
    date_create = fields.Datetime(string='Ngày tạo', default=fields.Datetime.now, readonly=True)
    
