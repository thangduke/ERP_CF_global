from odoo import models, fields, api, _

class Department(models.Model):
    _name = "employee.department"
    _description = "Phòng ban"

    name = fields.Char(string='Tên phòng ban', required=True)
    sequence = fields.Integer('Thứ tự')
    department_code = fields.Char('Mã phòng ban', required=True)
    active = fields.Boolean('Active', default=True)
    
    description = fields.Text('Mô tả')

    manager_id = fields.Many2one('employee.base', string='Quản lý')
    
    member_ids = fields.One2many('employee.base', 'department_id',
                                 string='Thành viên', domain=[('state', '!=', 'quit')])
    
    parent_id = fields.Many2one('employee.department', string='Ban cấp trên')
    child_ids = fields.One2many('employee.department', 'parent_id', string='Ban cấp dưới')
    
    employee3c_properties_definition = fields.PropertiesDefinition('Employee Properties 3C')
    total_employee = fields.Integer(compute='_compute_total_employee', string='Số thành viên', store=True)

    @api.depends('member_ids')
    def _compute_total_employee(self):
        for record in self:
            record.total_employee = len(record.member_ids)

