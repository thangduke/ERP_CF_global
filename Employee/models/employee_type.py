from odoo import models, fields, api
# Nhân sự toàn thời gian hoặc bán thời gian
# Nhân sự chính thức hoặc không chính thức
class EmployeeType(models.Model):
    _name = "employee.type"
    _description = "Phân loại nhân sự"

    name = fields.Char("Tên loại nhân sự", required=True)
    description = fields.Text('Mô tả')
    employee_type_code = fields.Char('Mã')
    state = fields.Boolean('Khả dụng', default=True)
    employee_ids = fields.One2many('employee.base', 'employee_type_2',
                                   string='Nhân sự', domain=[('state', '!=', 'quit')])
    position_type_id = fields.Many2one('position.type', 'Loại vị trí')
    total_employee = fields.Integer(compute='_compute_total_employee', string='Số nhân sự', store=True)

    @api.depends('employee_ids')
    def _compute_total_employee(self):
        for record in self:
            record.total_employee = len(record.employee_ids)

