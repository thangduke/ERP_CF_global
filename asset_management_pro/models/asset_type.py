from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AssetType(models.Model):
    _name = 'asset.type'
    _description = 'Chủng loại tài sản'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    name = fields.Char(string='Chủng loại', required=True, tracking=True)
    category_id = fields.Many2one('asset.category', string='Danh mục', required=True, tracking=True)


    asset_line_ids = fields.One2many('asset.asset', 'asset_type_id', string='Tài sản')


    create_date = fields.Datetime(string='Created Date', readonly=True, default=fields.Datetime.now)
    
    # Thông tin người tạo
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)  
        return employee.id if employee else False
    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                     default=lambda self: self._get_employee_default(), store=True)
    description = fields.Text(string='Mô tả')
    active = fields.Boolean(string='Active', default=True)