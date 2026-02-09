from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class MaterialTransfer(models.Model):
    _name = 'material.transfer'
    _description = 'Điều chuyển vật tư'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "create_date desc"

    name = fields.Char(string='Mã phiếu', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    source_store_id = fields.Many2one('store.list', string='Kho nguồn', required=True, domain="[('id', '!=', destination_store_id)]")
    destination_store_id = fields.Many2one('store.list', string='Kho đích', required=True, domain="[('id', '!=', source_store_id)]")
    
    transfer_date = fields.Datetime(string='Ngày điều chuyển', default=fields.Datetime.now, required=True)
    
    employee_id = fields.Many2one(
        'employee.base', 
        string='Người thực hiện',
        default=lambda self: self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1),
        required=True
    )
    
    state = fields.Selection([
        ('draft', 'Dự thảo'),
        ('done', 'Hoàn thành'),
        ('cancel', 'Hủy'),
    ], string='Trạng thái', default='draft', tracking=True)

    transfer_line_ids = fields.One2many('material.transfer.line', 'transfer_id', string='Chi tiết điều chuyển')
    
    notes = fields.Text(string='Ghi chú')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('material.transfer') or _('New')
        return super(MaterialTransfer, self).create(vals)

    def action_confirm(self):
        self.ensure_one()
        if not self.transfer_line_ids:
            raise UserError(_("Bạn phải thêm ít nhất một vật tư để điều chuyển."))

        for line in self.transfer_line_ids:
            # Tìm hoặc tạo bản ghi stock ở kho nguồn
            source_stock = self.env['material.stock.summary'].search([
                ('material_id', '=', line.material_id.id),
                ('store_id', '=', self.source_store_id.id),
                ('shelf_id', '=', line.source_shelf_id.id if line.source_shelf_id else False),
            ], limit=1)

            if not source_stock or source_stock.quantity < line.quantity:
                raise UserError(_("Vật tư '%s' trong kệ '%s' của kho nguồn không đủ số lượng để điều chuyển.") % (line.material_id.name, line.source_shelf_id.name or 'Chưa gán kệ'))

            # Trừ số lượng ở kho nguồn
            source_stock.quantity -= line.quantity

            # Tìm hoặc tạo bản ghi stock ở kho đích
            dest_stock = self.env['material.stock.summary'].search([
                ('material_id', '=', line.material_id.id),
                ('store_id', '=', self.destination_store_id.id),
                ('shelf_id', '=', line.destination_shelf_id.id if line.destination_shelf_id else False),
            ], limit=1)

            if not dest_stock:
                dest_stock = self.env['material.stock.summary'].create({
                    'material_id': line.material_id.id,
                    'store_id': self.destination_store_id.id,
                    'shelf_id': line.destination_shelf_id.id if line.destination_shelf_id else False,
                    'quantity': line.quantity,
                })
            else:
                # Cộng số lượng ở kho đích
                dest_stock.quantity += line.quantity

        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    @api.constrains('source_store_id', 'destination_store_id')
    def _check_stores(self):
        for record in self:
            if record.source_store_id and record.destination_store_id and record.source_store_id == record.destination_store_id:
                raise ValidationError(_("Kho nguồn và kho đích không được trùng nhau."))

class MaterialTransferLine(models.Model):
    _name = 'material.transfer.line'
    _description = 'Chi tiết điều chuyển vật tư'

    transfer_id = fields.Many2one('material.transfer', string='Phiếu điều chuyển', required=True, ondelete='cascade')
    
    material_id = fields.Many2one('material.list', string='Vật tư', required=True)
    
    quantity = fields.Float(string='Số lượng', required=True, default=1.0)
    
    source_store_id = fields.Many2one(related='transfer_id.source_store_id', store=True)
    destination_store_id = fields.Many2one(related='transfer_id.destination_store_id', store=True)

    source_shelf_id = fields.Many2one('shelf.list', string='Từ kệ', domain="[('store_id', '=', source_store_id)]")
    destination_shelf_id = fields.Many2one('shelf.list', string='Đến kệ', domain="[('store_id', '=', destination_store_id)]")
    
    available_quantity = fields.Float(string='Số lượng tồn', compute='_compute_available_quantity')

    @api.depends('material_id', 'source_store_id', 'source_shelf_id')
    def _compute_available_quantity(self):
        for line in self:
            if line.material_id and line.source_store_id:
                stock = self.env['material.stock.summary'].search([
                    ('material_id', '=', line.material_id.id),
                    ('store_id', '=', line.source_store_id.id),
                    ('shelf_id', '=', line.source_shelf_id.id if line.source_shelf_id else False),
                ], limit=1)
                line.available_quantity = stock.quantity if stock else 0
            else:
                line.available_quantity = 0

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_("Số lượng điều chuyển phải lớn hơn 0."))
            if line.quantity > line.available_quantity:
                raise ValidationError(_("Số lượng điều chuyển của vật tư '%s' không được vượt quá số lượng tồn kho.") % line.material_id.name)