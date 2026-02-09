from odoo import models, fields, api

class AssetLocation(models.Model):
    _name = 'asset.location'
    _description = 'Chủ sở hữu'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Tên chủ sở hữu', required=True, tracking=True)
    address = fields.Text(string='Địa chỉ')
    
    # Thông tin người tạo
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)  
        return employee.id if employee else False
    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                     default=lambda self: self._get_employee_default(), store=True)
    description = fields.Text(string='Mô tả')
    active = fields.Boolean(string='Active', default=True)