from odoo import models, fields, api


class ChangeExtraInfo(models.TransientModel):
    _name = 'change.extra.info'

    employee_id = fields.Many2one('employee.base', 'Họ và tên')
    user_id = fields.Many2one('res.users')
    name = fields.Char('Họ và tên')
    nationality = fields.Many2one('res.country', string="Quốc tịch")
    identification_id = fields.Char(string='Căn cước công dân', size=12)
    permanent_address = fields.Char('Địa chỉ thường trú')
    current_address = fields.Char('Nơi ở hiện tại')
    gender = fields.Selection([
        ('male', 'Nam'),
        ('female', 'Nữ'),
        ('other', 'Khác')], string='Giới tính')
    birthday = fields.Date("Ngày sinh")
    phone_number = fields.Char('Số điện thoại')

    @api.onchange('employee_id')
    def _compute_phone_number(self):
        self.nationality = self.employee_id.nationality
        self.identification_id = self.employee_id.identification_id
        self.permanent_address = self.employee_id.permanent_address
        self.current_address = self.employee_id.current_address
        self.gender = self.employee_id.gender
        self.birthday = self.employee_id.birthday
        self.phone_number = self.employee_id.mobile_phone

    @api.onchange('user_id')
    def _compute_name(self):
        self.name = self.user_id.name

    @api.model
    def create(self, vals):
        if 'employee_id' in vals :
            employee = self.env['employee.base'].browse(vals['employee_id'])
            employee.write({'nationality': vals['nationality'], 'identification_id': vals['identification_id'],
                            'gender': vals['gender'], 'birthday': vals['birthday'], 'name': vals['name'],
                            'permanent_address': vals['permanent_address'],
                            'mobile_phone': vals['phone_number'], 'current_address': vals['current_address']})

            user = self.env['res.users'].browse(vals['user_id'])
            user.write({'name': vals['name']})

        return super(ChangeExtraInfo, self).create(vals)
