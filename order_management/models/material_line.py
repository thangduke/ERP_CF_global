from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re

class MaterialLine(models.Model):
    _name = 'material.line'
    _description = 'Chi tiết vật tư po'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'
    _order = "name_sort_key asc, name asc"
    _rec_name = 'name'

    po_id = fields.Many2one('material.purchase.order', string='PO', ondelete='cascade')
    order_id = fields.Many2one(related='po_id.order_id',
        string="Chương trình", store=True, readonly=True
    )
    
    invoice_id = fields.Many2one('material.invoice', string='Invoice', ondelete='set null',readonly=True)
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)  
        return employee.id if employee else False
    employee_id = fields.Many2one('employee.base', 'Người tạo',readonly=True,
                                  default=lambda self: self._get_employee_default(), store=True)
    
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")
    entry_date = fields.Date(string='Thời gian nhập',readonly=True)
    
    name = fields.Char(string='Mã code vật tư', help='Mã code vật tư', readonly="1")
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
    mtr_no = fields.Char(string='Mtr#', help='Mã code vật tư', readonly="1")  # Mã vật tư / Mtr No
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
    
    # >> Định lượng và giá
    cons_qty = fields.Float(string='Cons.Qty', digits=(16, 3), help='Số lượng định mức', readonly=True)
    fct_qty = fields.Float(string='Fct.Qty', digits=(16, 3), help='Số lượng dự phòng hao hụt',compute='_compute_fct_qty' , readonly="1")
    est_qty = fields.Float(string='Est.Qty', digits=(16, 3), help='Số lượng đặt hàng', )
    act_qty = fields.Float(string='PO.Qty', digits=(16, 3), help='Số lượng nhập theo đợt')
    stock_qty = fields.Float(string='Stock.Qty', digits=(16, 3), help='Số lượng tồn kho hiện tại', readonly="1")

    percent_selection = fields.Selection(
        selection=[
            ('0.05', '5%'),
            ('0.10', '10%'),
            ('0.15', '15%'),
            ('0.20', '20%'),
            ('0.25', '25%'),
            ('0.30', '30%'),
            ('0.35', '35%'),
            ('0.40', '40%'),
            ('0.45', '45%'),
            ('0.50', '50%'),

        ],
        string='Phần trăm dự phòng',
        default='0.10',
        help='Chọn phần trăm dự phòng hao hụt'
    )
    percent = fields.Float(
        string='Phần trăm dự phòng (%)',
        default=0.10,
        digits=(5, 4),
        help='Nhập phần trăm dự phòng. Ví dụ: 0.1 = 10%, 0.05 = 5%'
    )

    @api.onchange('cons_qty', 'percent')
    def _onchange_est_qty(self):
        for rec in self:
            percent = rec.percent or 0.0
            rec.est_qty = (rec.cons_qty or 0.0) * percent  + (rec.cons_qty or 0.0)
             
    remaining_qty = fields.Float(string='SL còn lại', compute="_compute_remaining_qty", digits=(16, 3), store=True, default=0.0)
    
    @api.depends('est_qty', 'act_qty','remaining_qty')
    def _compute_remaining_qty(self):
        for rec in self:
            rec.remaining_qty = (rec.est_qty or 0.0) - (rec.act_qty or 0.0)

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

    @api.depends('est_qty', 'price', 'cif_price', 'fob_price', 'exwork_price')
    def _compute_total(self):
        for rec in self:
            rec.total = (rec.est_qty or 0.0) * (rec.price or 0.0)
            rec.cif_total = (rec.est_qty or 0.0) * (rec.cif_price or 0.0)
            rec.fob_total = (rec.est_qty or 0.0) * (rec.fob_price or 0.0)
            rec.exwork_total = (rec.est_qty or 0.0) * (rec.exwork_price or 0.0)       
            
    x_selected = fields.Boolean(string="Chọn")
    
    is_invoice_line = fields.Boolean(string='Dòng hóa đơn', default=False, 
        help="Đánh dấu dòng này là dòng hóa đơn để tránh xóa nhầm")
    
    @api.model
    def create(self, vals):
        cons_qty = vals.get('cons_qty', 0.0)
        percent = vals.get('percent', 0.10)
        # Nếu chưa nhập est_qty thì gán mặc định theo công thức
        if not vals.get('est_qty'):
            vals['est_qty'] = (cons_qty or 0.0) * percent + (cons_qty or 0.0)
        return super(MaterialLine, self).create(vals)
