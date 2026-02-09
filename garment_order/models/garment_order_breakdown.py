from odoo import models, fields, api
from odoo.exceptions import ValidationError, AccessError
import re

class GarmentOrderBreakdown(models.Model):
    _name = 'garment.order.breakdown'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'

# region (Phần 2) liên kết
    program_id = fields.Many2one('garment_program', required=True)

    style_id = fields.Many2one('garment_style', required=True)
    colorway_id = fields.Many2one('garment_colorway', required=True)
    size = fields.Many2one('garment_size', required=True)
# endregion

# region (Phần 1) THÔNG TIN ORDER BREAKDOWN
    order_qty = fields.Integer(required=True)
    
    test_qty = fields.Integer(required=True)
# endregion
