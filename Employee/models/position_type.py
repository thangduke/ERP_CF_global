from odoo import models, fields

class PositionType(models.Model):
    _name = "position.type"
    _description = "Phân loại vị trí"

    name = fields.Char(string='Loại vị trí', required=True)
    description = fields.Text('Mô tả')
    active = fields.Boolean(default=True)
    sequence = fields.Integer('Sequence')
    position_ids = fields.One2many('employee.position', 'position_type_id', 'Vị trí đã liên kết')
