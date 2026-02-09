from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re

class MaterialInvoiceLine(models.Model):
    _name = 'material.invoice.line'
    _description = 'Dòng vật tư trong phiếu nhập hàng'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "name_sort_key asc, name asc"
    _rec_name = 'name'
    
    invoice_id = fields.Many2one('material.invoice', string='Phiếu nhập', required=True, ondelete='cascade')
    po_line_id = fields.Many2one('material.line', string='Dòng PO gốc')
    receive_id = fields.Many2one('material.receive', string='Phiếu nhập kho', ondelete='cascade')
    
    entry_date = fields.Date(string='Ngày nhập', tracking=True)
       
    name = fields.Char(string='Mtr#',)
    name_sort_key = fields.Integer(compute='_compute_name_sort_key', string="Sort Key for Name", store=True, index=True)

    @api.depends('name')
    def _compute_name_sort_key(self):
        for rec in self:
            if rec.name:
                # Tách số từ chuỗi, ví dụ 'MI-123' -> 123
                numeric_part = re.findall(r'\d+', rec.name)
                rec.name_sort_key = int(numeric_part[0]) if numeric_part else 0
            else:
                rec.name_sort_key = 0

   #  program_customer_line_id = fields.Many2one('program.customer.line', string='Vật tư gốc', ondelete='cascade', required=True, tracking=True)                  
    position = fields.Char(string="Position", help="Vị trí vật tư",readonly="1")
    mtr_no = fields.Char(string='Mtr_no', help='Mã code vật tư', readonly="1")  # Mã vật tư / Mtr No
    mtr_type = fields.Many2one('material.type', string="Mtr Type", help="Loại vật tư", readonly="1")
    mtr_code = fields.Char(string='Mtr Code', help='Code item của nhà cung cấp', readonly="1")
    mtr_name = fields.Char(string="Mtr Name", help="Tên vật tư", readonly="1")
    rate = fields.Char(string="Unit", help='Ví dụ: mét, cuộn, cái...', readonly="1")
    
    # >> Kích thước
    dimension = fields.Char(string='Dimension', help="Kích thước vật tư", default=' ', readonly="1")

    # >> Màu sắc
    color_item = fields.Char(string="Color#", help="Mã item màu", readonly="1")
    color_code = fields.Char(string="Color Code", help="Mã code màu", readonly="1")
    color_name = fields.Char(string="Color Name", help="Tên màu", readonly="1")
    color_set = fields.Char(string="Color Set", help="Bộ màu", readonly="1")    

    # >> Thông tin nhà cung cấp
    supplier = fields.Many2one('supplier.partner', string="Supplier", help="Nhà cung cấp", readonly="1")
    
    supplier_index = fields.Char(string="Supplier#", related='supplier.supplier_index', help="Mã số nhà cung cấp")
    country = fields.Char(string="Quốc gia", help=" Quốc gia nhà cung cấp", readonly="1")

    est_qty = fields.Float(string='Est.Qty', digits=(16, 3), readonly="1", help='Số lượng cần theo định mức', tracking=True)
    act_qty = fields.Float(string='PO.Qty', digits=(16, 3),readonly="1", help='Số lượng đặt hàng theo đợt', tracking=True) 
    inv_qty = fields.Float(string='INV.Qty', digits=(16, 3), help='Số lượng trên invoice', tracking=True)
 


    # Price/FOB Price/EXW Price/
    price = fields.Float(string="Price",  digits=(16, 3),)
    cif_price = fields.Float(string="CIF.Price", digits=(16, 3), help="Giá bán cho khách hàng")
    fob_price = fields.Float(string="CIF.Price",  digits=(16, 3), help="Giá mua vào")
    exwork_price = fields.Float(string="EXW.Price", digits=(16, 3), help="Giá xuất xưởng")
    
    # >> Tổng thành tiền
    total = fields.Float(string="Total", compute="_compute_total", digits=(16, 3), )
    cif_total = fields.Float(string="CIF.Total", compute="_compute_total", digits=(16, 3),)
    fob_total = fields.Float(string="FOB.Total", compute="_compute_total", digits=(16, 3),)
    exwork_total = fields.Float(string="EXW.Total", compute="_compute_total", digits=(16, 3),)

    @api.depends('act_qty', 'price', 'cif_price', 'fob_price', 'exwork_price')
    def _compute_total(self):
        for rec in self:
            rec.total = (rec.act_qty or 0.0) * (rec.price or 0.0)
            rec.cif_total = (rec.act_qty or 0.0) * (rec.cif_price or 0.0)
            rec.fob_total = (rec.act_qty or 0.0) * (rec.fob_price or 0.0)
            rec.exwork_total = (rec.act_qty or 0.0) * (rec.exwork_price or 0.0)  


    x_selected = fields.Boolean(string="Chọn")
    