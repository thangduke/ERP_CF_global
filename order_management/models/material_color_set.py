from odoo import models, fields, api

class MaterialColorSet(models.Model):
    _name = 'material.color.set'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Bộ mã màu vật tư'
    
    name = fields.Char(string='Tên bộ màu', required=True ,tracking=True)
    description = fields.Char(string='Mô tả')
    color= fields.Char(string="Màu sắc", )
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
        ('name_uniq', 'unique(name)', 'Tên bộ màu đã tồn tại. Vui lòng chọn một tên khác!')
    ]