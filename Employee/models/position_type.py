from odoo import models, fields

class PositionType(models.Model):
    _name = "position.type"
    _description = "Vị trí công tác"

    name = fields.Char(string='Vị trí công tác', required=True)
    description = fields.Text('Mô tả')
    active = fields.Boolean(default=True)
    sequence = fields.Integer('Sequence')

