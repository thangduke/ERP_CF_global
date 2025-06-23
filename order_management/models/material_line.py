from odoo import models, fields, api

class MaterialLine(models.Model):
    _name = 'material.line'
    _description = 'Chi tiết vật tư po'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'
    _order = "create_date desc"

    po_id = fields.Many2one('material.purchase.order', string='PO', ondelete='cascade')
    order_id = fields.Many2one(related='po_id.order_id',
        string="Đơn hàng", store=True, readonly=True
    )
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)  
        return employee.id if employee else False
    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self._get_employee_default(), store=True)
    
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")
    entry_date = fields.Date(string='Thời gian nhập')
    
    position = fields.Char(string="Vị trí sử dụng", help="Số thứ tự vị trí") 
    mtr_no = fields.Char(string='Mã vật tư', )  # Mã vật tư /Mtr No     
    mtr_type = fields.Many2one('material.type',string="Type", ) # Loại vật tư

    mtr_code = fields.Char(string='Code item của nhà cung cấp')  # Mã nội bộ / Mtr Code
    mtr_name = fields.Char(string='Tên vật tư ')  # Tên vật tư / Mtr Name

    dimension = fields.Char(string='Kích thước')  # Kích thước / Dimension
    color_item = fields.Char(string='Mã màu vật tư')  # Mã màu vật tư / Color Item
    
    color_name = fields.Char(string='Tên màu')  # Tên màu /Color Name
    color_set = fields.Char(string='Color Set')  # Bộ màu (nếu có)/ Color Set
    color_code = fields.Char(string='Color Code')  # Mã code màu / Color Code


    est_qty = fields.Float(string='SL ước tính',digits=(16, 3), help='Số lượng ước tính')  # Ước tính / Est Qty
    act_qty = fields.Float(string='SL thực tế',digits=(16, 3), help='Số lượng thực tế nhận')  # Thực tế / Act Qty
    
    rate = fields.Char(string='Đơn vị tính', help='Ví dụ: mét, cuộn, cái...')
    price = fields.Float(string='Đơn giá',digits=(16, 3), store=True)  # Thành tiền / Price
    supplier = fields.Many2one('supplier.partner', string="Nhà cung cấp", help="Nhà cung cấp vật tư")
    country = fields.Char(string="Quốc gia")
    cif_price = fields.Float(string="Giá CIF",digits=(16, 3), help="Giá bán cho khách hàng")
    fob_price = fields.Float(string="Giá FOB",digits=(16, 3), help="Giá mua vào")
    exwork_price = fields.Float(string="Giá EXW",digits=(16, 3), help="Giá xuất xưởng")
    total = fields.Float(string="Tổng thành tiền", compute="_compute_total",digits=(16, 3), store=True, default=0.0)
    @api.depends('est_qty', 'price') 
    def _compute_total(self):
        for rec in self:
            rec.total = (rec.est_qty or 0.0) * (rec.price or 0.0)
            
    x_selected = fields.Boolean(string="Chọn")
