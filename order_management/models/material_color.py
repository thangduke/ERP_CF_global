from odoo import models, fields, api


class MaterialColor(models.Model):
    _name = 'material.color'
    _description = 'Màu sắc vật tư'
    
    name = fields.Char(string='Mã màu vật tư',default='New', readonly=True, tracking=True)
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('material.color') or 'New'
        return super(MaterialColor, self).create(vals)
    
    color_name = fields.Char(string='Tên màu', tracking=True, required=True)
    color_code = fields.Char(string='Color Code')
    color_set_id = fields.Many2one('material.color.set')
    active = fields.Boolean(string='Kích hoạt', default=True)
    color = fields.Char(string="Màu sắc", tracking=True)
    # Thông tin người tạo
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)  
        return employee.id if employee else False
    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self._get_employee_default(), store=True)
    
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")
    
    date_create = fields.Datetime(string='Ngày tạo', default=fields.Datetime.now, readonly=True)
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Mã màu vật tư đã tồn tại. Vui lòng chọn một mã khác!'),
        ('color_code_uniq', 'unique(color_code)', 'Mã màu đã tồn tại. Vui lòng chọn một mã khác!')
    ]