from odoo import models, fields, api
# Model dòng định mức vật tư
class MaterialNormLine(models.Model):
    _name = 'material.norm.line'
    _description = 'Định mức vật tư theo Style (Color/Size)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'consumption'

    color_size_id = fields.Many2one(
        'product.color.size',
        string="Style (Color/Size)",
        required=True,
        readonly=True,
        ondelete='cascade',
        default=lambda self: self.env.context.get('active_id') 
            if self.env.context.get('active_model') == 'product.color.size' else self.env.context.get('default_color_size_id')
    )
    position = fields.Char( store=True, string="Position", help="Vị trí vật tư")
    program_customer_id = fields.Many2one('program.customer', 
        string="Vật tư", required=True, ondelete='cascade'
    )
    size_id = fields.Many2one(
        'product.size',
        string="Size",
        related='color_size_id.size_id',
        store=True,
        readonly=True,
    )
    consumption = fields.Float(string='Định mức', digits=(16, 3), default=0.0, 
        help='Số lượng vật tư cần cho size này', tracking=True
    )

    _sql_constraints = [
        ('uniq_norm_per_style',
         'unique(program_customer_id, color_size_id)',
         'Định mức cho Vật tư và Style này đã tồn tại!')
    ]


