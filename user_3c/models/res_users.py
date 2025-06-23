from odoo import models, fields, api, _


class User3C(models.Model):
    _inherit = ['res.users']

    @api.model
    def action_open_my_account_info_form(self):
        # Lấy user hiện tại
        current_user = self.env.user

        if current_user:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Thông tin tài khoản',
                'res_model': 'res.users',
                'view_mode': 'form',
                'res_id': current_user.id,
                'view_id': self.env.ref('base.view_users_form_simple_modif').id,
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window_close',
            }

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Template để nhập tài khoản người dùng'),
            'template': '/user_3c/static/xlsx/Account.xlsx'
        }]