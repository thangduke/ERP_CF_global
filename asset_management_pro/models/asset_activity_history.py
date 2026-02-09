from odoo import models, fields, api

class AssetActivityHistory(models.Model):
    _name = 'asset.activity.history'
    _description = 'Lịch sử hoạt động tài sản'
    _order = 'date desc'

    asset_id = fields.Many2one('asset.asset', string='Tài sản', required=True, ondelete='cascade')
    description = fields.Text(string='Nội dung')
    date = fields.Datetime(string='Ngày', default=fields.Datetime.now, readonly=True)
    employee_id = fields.Many2one('employee.base', string='Người thực hiện', readonly=True, default=lambda self: self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1))
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người thực hiện")