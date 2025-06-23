from odoo import models, fields, api

class ProgramCustomer(models.Model):
    _name = 'program.customer'
    _description = 'Định mức khách hàng'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'
    _order = "create_date desc"
    
    color_size_id = fields.Many2one('product.color.size', string="Biến thể (Màu + Size)", ondelete='cascade')
    warehouse_material_id = fields.Many2one('warehouse.order', string='Đơn hàng')
    
    position = fields.Char(string="Vị trí sử dụng", help="Số thứ tự vị trí") 
    mtr_type = fields.Many2one('material.type',string="Type", ) # Loại vật tư /Type
    mtr_name = fields.Char(string='Tên vật tư ')  # Tên vật tư / Mtr Name
    mtr_code = fields.Char(string='Code item của nhà cung cấp')  # Mã nội bộ / Mtr Code
    mtr_no = fields.Char(string='Mã vật tư', )  # Mã vật tư /Mtr#   

    dimension = fields.Char(string='Kích thước')  # Kích thước / Dimension
   
    material_color_id = fields.Many2one('material.color', string='Màu vật tư')
    color_item = fields.Char(string='Mã item màu',related='material_color_id.name', store=True) # Mã màu vật tư / Color# 
    color_name = fields.Char(string='Tên màu',related='material_color_id.color_name', store=True) # Tên màu /Color Name 
    color_set = fields.Char(string='Bộ màu',related='material_color_id.color_set_id.name', store=True ) # Bộ màu (nếu có)/ Color Set 
    color_code = fields.Char(string='Mã code màu',related='material_color_id.color_code', store=True) # Mã code màu / Color Code 


    rate = fields.Char(string='Đơn vị tính', help='Ví dụ: mét, cuộn, cái...')
    price = fields.Float(string='Đơn giá',digits=(16, 3), store=True)  # Thành tiền / Price
    
    supplier = fields.Many2one('supplier.partner', string="Nhà cung cấp", help="Nhà cung cấp vật tư")

    est_qty = fields.Float(string='SL ước tính',digits=(16, 3), help='Số lượng ước tính')  # Ước tính / Est.Total
    act_qty = fields.Float(string='SL thực tế',digits=(16, 3), help='Số lượng thực tế nhận')  # Thực tế / P/O Total
    
    country = fields.Char(string="Quốc gia")    
    @api.onchange('supplier')
    def _onchange_supplier(self):
        for rec in self:
            if rec.supplier and rec.supplier.country_id:
                rec.country = rec.supplier.country_id.name
            else:
                rec.country = ''
    size_id = fields.Many2one('product.size',digits=(16, 3), string="Size", required=True)
    cif_price = fields.Float(string="Giá CIF",digits=(16, 3), help="Giá bán cho khách hàng", default=0.0)
    fob_price = fields.Float(string="Giá FOB",digits=(16, 3), help="Giá mua vào", default=0.0)
    exwork_price = fields.Float(string="Giá EXW", help="Giá xuất xưởng",digits=(16, 3), default=0.0)
    total = fields.Float(string="Tổng thành tiền", compute="_compute_total",digits=(16, 3), store=True, default=0.0)
    x_selected = fields.Boolean(string="Chọn", default=False)
    @api.depends('est_qty', 'price')
    def _compute_total(self):
        for rec in self:
            rec.total = (rec.est_qty or 0.0) * (rec.price or 0.0)    
            
# Tạo model trung gian tổng hợp vật tư     
class WarehouseOrderMaterialLineSummary(models.TransientModel):
    _name = 'warehouse.order.material.line.summary'
    _description = 'Tổng hợp vật tư theo đơn hàng (tạm thời)'

    order_id = fields.Many2one('warehouse.order', string='Đơn hàng')
    product_code_id = fields.Many2one('product.code', string='Mã sản phẩm')
    color_size_id = fields.Many2one('product.color.size', string="Biến thể (Màu + Size)")
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