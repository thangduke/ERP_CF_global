from odoo import models, fields, api

class GarmentSize(models.Model):
    _name = 'garment.size'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Kích thước sản phẩm'

    name = fields.Char ( string="Size", required=True, tracking=True)
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
    ''''''
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Size đã tồn tại. Vui lòng chọn một tên khác!')
    ]
    
