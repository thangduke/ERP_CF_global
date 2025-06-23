from odoo import models, fields, api
from odoo.exceptions import ValidationError

class MaterialDelivery(models.Model):
    _name = 'material.delivery'
    _description = 'Xuất kho'

    delivery_no = fields.Char(string="Số phiếu xuất", copy=False, readonly=True)

    @api.model
    def create(self, vals):
        if not vals.get('delivery_no') or vals['delivery_no'] == '/':
            vals['delivery_no'] = self.env['ir.sequence'].next_by_code('material.delivery')
        return super().create(vals)
    
    # Gán dòng vật tư liên quan
    program_line_ids = fields.One2many('program.customer', compute='_compute_preview_lines', string="vật tư định mức", store=False) 

                  
                 
    date_delivery = fields.Date(string="Ngày xuất", default=fields.Date.today)
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)
        return employee.id if employee else False

    employee_id = fields.Many2one(
        'employee.base', 'Nhân viên xuất',
        default=lambda self: self._get_employee_default(), store=True
    )   
    # Thông tin nơi nhập
    store_id = fields.Many2one('store.list', string="Kho nhập", required=True)
    shelf_id = fields.Many2one(
        'shelf.list',
        string="Kệ chứa",
        required=True,
        domain="[('store_id', '=', store_id)]"
    )

    # Liên kết hóa đơn nếu có
    order_id = fields.Many2one('warehouse.order', string="Đơn hàng")
    '''        
    program_id = fields.Many2one(
        'product.code',
        string="Mã hàng",
        required=True,
        domain="[('warehouse_order_id', '=', order_id)]"
    )'''
    
    customer_id = fields.Many2one('customer.cf', string="Khách hàng")
    
    production_id = fields.Char( string="Chuyền sản xuất", )

    receiver = fields.Many2many ('employee.base', string="Người nhận")

    purpose = fields.Char(string="Mục đích xuất kho")
    
    def action_confirm(self):
        """Xác nhận xuất kho và cập nhật tồn kho"""
        for line in self.material_line_ids:
            stock = self.env['material.stock'].search([
                ('store_id', '=', self.store_id.id),
                ('shelf_id', '=', self.shelf_id.id),
                ('mtr_no', '=', line.mtr_no)
            ], limit=1)

            if not stock or stock.act_qty < line.act_qty:
                raise ValidationError(
                    f"Kệ {self.shelf_id.name} trong kho {self.store_id.name} không đủ vật tư {line.mtr_name} để xuất."
                )

            # Trừ số lượng tồn kho
            stock.act_qty -= line.act_qty

            # Nếu số lượng tồn kho bằng 0, có thể xóa bản ghi (tùy yêu cầu)
            if stock.act_qty <= 0:
                stock.unlink() 