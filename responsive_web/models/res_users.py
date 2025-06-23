from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def create(self, vals):
        if 'home_action_id' not in vals:
            action = self.env.ref('responsive_web.action_web_responsive', raise_if_not_found=False)
            if action:
                vals['home_action_id'] = action.id
        return super().create(vals)
