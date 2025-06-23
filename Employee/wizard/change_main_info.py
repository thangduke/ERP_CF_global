from odoo import models, fields, api, _


class ChangeMainInfo(models.TransientModel):
    _name = 'change.main.info'

    employee_id = fields.Many2one('employee.base', 'Họ và tên')
    user_id = fields.Many2one('res.users')
    position_id = fields.Many2one('employee.position', 'Vị trí', domain="[('department_id', '=', department_id)]")
    start_date = fields.Date(string="Ngày bắt đầu")
    official_date = fields.Date(string='Ngày chính thức')
    department_id = fields.Many2one('employee.department', 'Phòng ban')

    employee_type_2 = fields.Many2one('employee.type', 'Phân loại nhân sự')
    parent_id = fields.Many2one('employee.base', string="Cấp trên trực tiếp", domain=[('state', '!=', 'quit')])
    email = fields.Char("Email")
    image_1920 = fields.Image("Ảnh đại diện")
    employee_index = fields.Char(string='Mã nhân sự')
    company_id = fields.Many2one(related='user_id.company_id')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)

    @api.onchange('employee_id')
    def _compute_phone_number(self):
        self.position_id = self.employee_id.position_id
        self.start_date = self.employee_id.start_date
        self.official_date = self.employee_id.official_date
        self.department_id = self.employee_id.department_id

        self.employee_type_2 = self.employee_id.employee_type_2
        self.parent_id = self.employee_id.parent_id
        self.image_1920 = self.employee_id.image_1920
        self.employee_index = self.employee_id.employee_index
    @api.onchange('user_id')
    def _compute_name(self):
        self.email = self.user_id.email

    @api.model
    def create(self, vals):

        if 'employee_id' in vals and 'user_id' in vals:

            employee = self.env['employee.base'].browse(vals['employee_id'])

            employee.write({'position_id': vals['position_id'], 'start_date': vals['start_date'],
                            'official_date': vals['official_date'], 'department_id': vals['department_id'],
                            'employee_type_2': vals['employee_type_2'],
                            'parent_id': vals['parent_id'], 'image_1920': vals['image_1920'],
                            'employee_index': vals['employee_index']})

            user = self.env['res.users'].browse(vals['user_id'])

            user.write({'email': vals['email']})

        return super(ChangeMainInfo, self).create(vals)

