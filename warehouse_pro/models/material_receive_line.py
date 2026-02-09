from odoo import models, fields, api
import re
from odoo.exceptions import ValidationError

class MaterialReceiveLine(models.Model):
    _name = 'material.receive.line'
    _description = 'vật tư trong phiếu nhập kho'
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
    entry_date = fields.Datetime(string='Thời gian nhập')
             
    # Liên kết module mã invoice 
    order_id = fields.Many2one('warehouse.order', string="Chương trình",  store=True, 
                               help="Chọn chương trình liên quan đến vật tư nhập kho.")

    store_id = fields.Many2one('store.list', string="Kho chứa", )
    shelf_id = fields.Many2one('shelf.list', string="Kệ chứa", )
    shelf_level_id = fields.Many2one('shelf.level', string="Khoang chứa",)
    is_selected = fields.Boolean(string="Chọn")
   
    # origin_line_id = fields.Many2one('material.line', string="Dòng gốc (Invoice)")
    
    receive_id = fields.Many2one('material.receive', string="Mã nhập kho", required=True, ondelete='cascade')
    invoice_line_id = fields.Many2one('material.invoice.line', string="Dòng Hóa đơn Gốc", readonly=True, index=True)
    # This field will be filled in AFTER saving the receive record
    material_id = fields.Many2one("material.item.line", string="Dòng Vật tư Gốc", readonly=True)
    
    
    name = fields.Char( string="Mtr#")
    position = fields.Char( string="Position" , store=True)
    mtr_no = fields.Char( string='Mtr_no' , store=True)
    mtr_no_sort_key = fields.Integer( string="Sort Key", store=True)
    mtr_type = fields.Many2one('material.type',string="Type",  store=True)
    mtr_name = fields.Char( string='Mtr_name', store=True)
    mtr_code = fields.Char( string='Mtr_code', store=True)
    rate = fields.Char( string="Unit", store=True)
    
    dimension = fields.Char( string='Dimension', store=True)
    
    color_item = fields.Char(string="Color#", help="Mã item màu",)
    color_code = fields.Char(string="Color#",  help="Mã code màu", store=True)
    color_name = fields.Char(string="Color_name",  help="Tên màu", store=True)
    color_set = fields.Char(string="Color_set",  help="Bộ màu", store=True)

    supplier = fields.Many2one('supplier.partner', string="Supplier", help="Nhà cung cấp vật tư", store=True)
    country = fields.Char( string="Country", store=True)

    # Transactional Fields
    price = fields.Float(string="Price", digits=(16, 3), store=True)
    cif_price = fields.Float(string="CIF.Price", digits=(16, 3), help="Giá bán cho khách hàng", store=True)
    fob_price = fields.Float(string="FOB.Price", digits=(16, 3), help="Giá mua vào", store=True)
    exwork_price = fields.Float(string="EXW.Price",  digits=(16, 3), help="Giá xuất xưởng", store=True)

    inv_qty = fields.Float(string="SL Hóa đơn", digits=(16, 3), store=True)
                
    qty = fields.Float(string='SL Nhập', digits=(16, 3), store=True, help='Số lượng nhập')  # Thực tế / Act Qty
        
    subtotal = fields.Float("Thành tiền", compute="_compute_subtotal")

    @api.depends("qty", "price")
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.qty * rec.price

