from odoo import models, fields, api


class ChangeManagers(models.TransientModel):
    _name = 'change.managers'

    employee_id = fields.Many2one('employee.base', 'Họ và tên')
    parent_ids = fields.Many2many('employee.base', 'change_employee_manager_rel'
                                  , 'employee_id', 'manager_id', string="Quản lý",
                                  )

    @api.onchange('employee_id')
    def _compute_managers(self):
        self.parent_ids = self.employee_id.parent_ids

    @api.model
    def create(self, vals):
        res = super(ChangeManagers, self).create(vals)

        employee = self.env['employee.base'].browse(res.employee_id.id)

        old_managers = employee.parent_ids
        new_managers = res.parent_ids

        managers_to_remove = old_managers - new_managers
        managers_to_add = new_managers - old_managers

        if managers_to_remove:
            employee.write({'parent_ids': [(3, manager.id) for manager in managers_to_remove]})

        if managers_to_add:
            employee.write({'parent_ids': [(4, manager.id) for manager in managers_to_add]})

        return res
