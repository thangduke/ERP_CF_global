from odoo import models, fields, api


class AssetStatus(models.Model):
    _name = 'asset.status'
    _description = 'Trạng thái tài sản'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    color = fields.Char(string="Màu sắc", tracking=True)
    description = fields.Text(string='Mô tả')
    active = fields.Boolean(string='Active', default=True)

    # Thông tin người tạo
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)
        return employee.id if employee else False
    
    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self._get_employee_default(), store=True, readonly=True)
    
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")
    
    date_create = fields.Datetime(string='Ngày tạo', default=fields.Datetime.now, readonly=True)