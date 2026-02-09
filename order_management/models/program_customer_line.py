from odoo import models, fields, api
from odoo.exceptions import ValidationError, AccessError

class ProgramCustomerLine(models.Model):
    _name = 'program.customer.line'
    _description = 'Chi tiết vật tư'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name_display'


    name_display= fields.Char(
        string="Name Display", 
        compute='_compute_name_display', 
        store=True, 
        help='Tên vật tư hiển thị'
    )
    
    @api.depends('name', 'mtr_type.item_type')
    def _compute_name_display(self):
        for rec in self:
            if rec.mtr_type and rec.mtr_type.item_type and rec.name and rec.name != 'New':
                rec.name_display = f"{rec.mtr_type.item_type}{rec.name}"
            else:
                rec.name_display = rec.name
    
    name = fields.Char(string="Mtr_no", help='Mã code vật tư', readonly=True, default='New', copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('program.customer.line') or 'New'
        return super(ProgramCustomerLine, self).create(vals_list)
    
    position = fields.Char(string="Position", help="Vị trí vật tư")  # Vị trí vật tư / Position
    mtr_type = fields.Many2one('material.type', string="Mtr Type", help="Loại vật tư")
    mtr_code = fields.Char(string='Mtr Code', help='Code item của nhà cung cấp', required=True)  # Mã nội bộ / Mtr Code
    mtr_name = fields.Char(string="Mtr Name", help="Tên vật tư")  # Tên vật tư / Mtr Name
    rate = fields.Char(string="Unit", related='rate_id.name', store=True, help='Ví dụ: mét, cuộn, cái...')
    rate_id = fields.Many2one('material.rate', string="Unit", required=True, help='Ví dụ: mét, cuộn, cái...')
      # Mô tả vật tư / Description
    description = fields.Char(string='Mô tả', help="Mô tả vật tư")
    
    @api.constrains('mtr_code')
    def _check_unique_mtr_code(self):
        for rec in self:
            if rec.mtr_code:
                # Case-insensitive search
                existing = self.search([('mtr_code', '=ilike', rec.mtr_code), ('id', '!=', rec.id)])
                if existing:
                    raise ValidationError(f"Mã vật tư (Mtr Code) '{rec.mtr_code}' đã tồn tại.")
