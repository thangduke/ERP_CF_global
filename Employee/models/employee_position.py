from odoo import models, fields, api
class Position(models.Model):
    _name = "employee.position"
    _description = "Vị trí công việc"

    name = fields.Char(string='Vị trí công việc', required=True)
    description = fields.Text("Mô tả")
    position_code = fields.Char('Mã vị trí')
    sequence = fields.Integer('Sequence')
    employee_ids = fields.One2many('employee.base', 'position_id',
                                   string='Nhân sự', domain=[('state', '!=', 'quit')])
    department_id = fields.Many2one('employee.department', string='Bộ phận')
    total_employee = fields.Integer(compute='_compute_total_employee', string='Số nhân sự', store=True)

    @api.depends('employee_ids')
    def _compute_total_employee(self):
        for record in self:
            record.total_employee = len(record.employee_ids)


