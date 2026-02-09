from odoo import api, models, fields

class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def action_open_company_info_form(self):
        current_user = self.env.user

        company = self.env['res.company'].search([('id', '=', current_user.company_id.id)], limit=1)

        if company:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Thông tin công ty',
                'res_model': 'res.company',
                'view_mode': 'form',
                'res_id': company.id,  
                'target': 'current',
                'flags': {'create': False},

            }
        else:
            return {
                'type': 'ir.actions.act_window_close',
            }