from odoo import models, fields, api

class ShelfShelfMaterialLine(models.Model):
    _name = 'shelf.material.line'
    _description = 'vật tư trong kệ (đã nhập kho)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'
    _order = "create_date desc"

    # Liên kết module mã invoice 
    shelf_id = fields.Many2one('shelf.list', string="Kệ chứa", required=True)
    stock_id = fields.Many2one('store.list', string="Kho chứa", required=True)
    
    # origin_line_id = fields.Many2one('material.line', string="Dòng gốc (Invoice)")
    
    receive_id = fields.Many2one('material.receive', string="Mã nhập kho", required=True)
    
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

    length = fields.Float(string='Length (m)', help='Chiều dài cuộn hoặc dây')  # Chiều dài / Length (m)

    est_qty = fields.Float(string='SL ước tính', help='Số lượng ước tính')  # Ước tính / Est Qty
    act_qty = fields.Float(string='SL thực tế', help='Số lượng thực tế nhận')  # Thực tế / Act Qty
    
    rate = fields.Char(string='Đơn vị tính', help='Ví dụ: mét, cuộn, cái...')
    price = fields.Float(string='Đơn giá', store=True)  # Thành tiền / Price
    supplier = fields.Char( string="Nhà cung cấp", help="Nhà cung cấp vật tư")
    country = fields.Char(string="Quốc gia")
    cif_price = fields.Float(string="Giá CIF", help="Giá bán cho khách hàng")
    fob_price = fields.Float(string="Giá FOB", help="Giá mua vào")
    exwork_price = fields.Float(string="Giá EXW", help="Giá xuất xưởng")
    total = fields.Float(string="Tổng thành tiền",  store=True)     
   


    @api.depends('act_qty','price')
    def _compute_total(self):
        for line in self:
            line.total = line.act_qty * line.price if line.act_qty and line.price else 0.0
            
    x_selected = fields.Boolean(string="Chọn")


class ShelfMaterialLineSummary(models.TransientModel):
    _name = 'shelf.material.line.summary'
    _description = 'Tổng hợp vật tư trong kệ/kho (tạm thời)'

    shelf_id = fields.Many2one('shelf.list', string="Kệ chứa")
    stock_id = fields.Many2one('store.list', string="Kho chứa")
    
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

    length = fields.Float(string='Length (m)', help='Chiều dài cuộn hoặc dây')  # Chiều dài / Length (m)

    est_qty = fields.Float(string='SL ước tính', help='Số lượng ước tính')  # Ước tính / Est Qty
    act_qty = fields.Float(string='SL thực tế', help='Số lượng thực tế nhận')  # Thực tế / Act Qty
    
    rate = fields.Char(string='Đơn vị tính', help='Ví dụ: mét, cuộn, cái...')
    price = fields.Float(string='Đơn giá', store=True)  # Thành tiền / Price
    supplier = fields.Char( string="Nhà cung cấp", help="Nhà cung cấp vật tư")
    country = fields.Char(string="Quốc gia")