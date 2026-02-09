from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re

class MaterialDeliveryLine(models.Model):
    _name = "material.delivery.line"
    _description = 'Vật tư xuất kho'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'
    _order = "mtr_no_sort_key asc, create_date desc"
    _rec_name = 'name'
       
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)  
        return employee.id if employee else False
    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self._get_employee_default(), store=True)
    
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")
    
    order_id = fields.Many2one('warehouse.order', string="Chương trình",  store=True, 
                               help="Chọn chương trình liên quan đến vật tư xuất kho.")

    store_id = fields.Many2one('store.list', string="Kho xuất",required=True )
    
    entry_date = fields.Date(string='Thời gian xuất kho')
    
    delivery_id = fields.Many2one('material.delivery', string="Phiếu xuất kho", ondelete='cascade')
    material_id = fields.Many2one("material.item.line", string="Dòng Vật tư")
    
    position = fields.Char(related='material_id.position', string="Position")
    
    name = fields.Char(related='material_id.name', string="Mtr#")
    
    mtr_no = fields.Char(related='material_id.mtr_no', string='Mtr_no')  # Mã vật tư /Mtr No
    mtr_no_sort_key = fields.Integer(related='material_id.mtr_no_sort_key', string="Sort Key")
    
    mtr_type = fields.Many2one('material.type',string="Mtr_type", related='material_id.mtr_type', store=False)
    mtr_name = fields.Char(related='material_id.mtr_name', string='Mtr_name')
    mtr_code = fields.Char(related='material_id.mtr_code', string='Mtr_Code')
    rate = fields.Char(related='material_id.rate', string="Unit")
    
    dimension = fields.Char(related='material_id.dimension', string='Dimension')
    
    color_item = fields.Char(string="Color#", related='material_id.color_item', help="Mã item màu",)
    color_code = fields.Char(string="Color_code", related='material_id.color_code', help="Mã code màu")
    color_name = fields.Char(string="Color_name", related='material_id.color_name', help="Tên màu")
    color_set = fields.Char(string="Color_set", related='material_id.color_set', help="Bộ màu")

    supplier = fields.Many2one('supplier.partner', string="Supplier", help="Nhà cung cấp vật tư", related='material_id.supplier',)
    country = fields.Char(related='material_id.country', string="Country")

    # Transactional Fields
    price = fields.Float(string="Price", related='material_id.price', digits=(16, 3),)
    cif_price = fields.Float(string="CIF.Price", related='material_id.cif_price', digits=(16, 3), help="Giá bán cho khách hàng")
    fob_price = fields.Float(string="FOB.Price", related='material_id.fob_price', digits=(16, 3), help="Giá mua vào")
    exwork_price = fields.Float(string="EXW.Price", related='material_id.exwork_price', digits=(16, 3), help="Giá xuất xưởng")

    cons_qty = fields.Float("Cons.Qty", readonly="1", digits=(16, 3), help="Số lượng định mức") 
      
    qty = fields.Float("Est.Qty", digits=(16, 3), help="Số lượng vật tư xuất kho", tracking=True)
     
    subtotal = fields.Float("Thành tiền", compute="_compute_subtotal")

    @api.depends("qty", "price")
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.qty * rec.price
            
            