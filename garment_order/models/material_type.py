from odoo import models, fields, api

class MaterialType(models.Model):
    _name = 'material.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Material Type'
    
    name = fields.Char(string='Mã loại vật tư',tracking=True)
    item_type = fields.Char(string='Item.Type', compute='_compute_item_type', store=True)

    @api.depends('name')
    def _compute_item_type(self):
        for rec in self:
            if rec.name:
                rec.item_type = rec.name[:2]
            else:
                rec.item_type = ''
                
    name_type = fields.Char(string='Tên loại vật tư', required=True)

    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)  
        return employee.id if employee else False
    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self._get_employee_default(), store=True)
    
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")
    
    date_create = fields.Datetime(string="Ngày tạo", default=fields.Datetime.now, readonly=True)
    active = fields.Boolean(string='Kích hoạt', default=True)
    description = fields.Text(string='Mô tả')
    description_display = fields.Text('Mô tả', compute='_compute_description_display')

    @api.depends('description')
    def _compute_description_display(self):
        for record in self:
            if record.description:
                record.description_display = record.description
            else:
                record.description_display = 'Không có mô tả'
                
    # Thêm SQL constraint
    _sql_constraints = [
        ('unique_type_name', 'UNIQUE(name)', 'Loại vật tư đã tồn tại!')
    ]