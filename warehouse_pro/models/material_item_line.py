from odoo import models, fields, api
import re
from odoo.exceptions import ValidationError

class MaterialItemLine(models.Model):
    _name = 'material.item.line'
    _description = 'vật tư gốc & thẻ kho'
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
    

    name = fields.Char(string="Mtr#", help='Mã code định mức', compute='_compute_name', readonly=True,  ) 
    
    @api.depends('mtr_no', 'color_item', 'dimension')
    def _compute_name(self):
        for rec in self:
            parts = [
                rec.mtr_no or '',
                rec.color_item or '',
                rec.dimension or ''
            ]
            rec.name = '.'.join(filter(None, parts))
                
    mtr_no = fields.Char(string='Mtr_no', )  # Mã vật tư /Mtr No     
    mtr_no_sort_key = fields.Integer(compute='_compute_mtr_no_sort_key', string="Sort Key for Mtr No", store=True, index=True)

    @api.depends('mtr_no')
    def _compute_mtr_no_sort_key(self):
        for rec in self:
            if rec.mtr_no:
                # Tách số từ chuỗi, ví dụ 'MI-123' -> 123
                numeric_part = re.findall(r'\d+', rec.mtr_no)
                rec.mtr_no_sort_key = int(numeric_part[0]) if numeric_part else 0
            else:
                rec.mtr_no_sort_key = 0
                
    position = fields.Char(string="Position", help="Số thứ tự vị trí") 
         
    mtr_type = fields.Many2one('material.type',string="Mtr_type", ) # Loại vật tư

    mtr_code = fields.Char(string='Mtr_Code', help="Mã nội bộ / Mtr Code")  # Mã nội bộ / Mtr Code
    mtr_name = fields.Char(string='Mtr_name', help="Tên vật tư / Mtr Name")  # Tên vật tư / Mtr Name
    
    rate = fields.Char(string="Unit", help='Ví dụ: mét, cuộn, cái...')
    # >> Kích thước
    dimension = fields.Char(string='Dimension', help="Kích thước vật tư", default=' ')

    # >> Màu sắc
    color_item = fields.Char(string="Color#", help="Mã item màu",)
    color_code = fields.Char(string="Color Code", help="Mã code màu")
    color_name = fields.Char(string="Color Name", help="Tên màu")
    color_set = fields.Char(string="Color Set", help="Bộ màu")

    supplier = fields.Many2one('supplier.partner', string="Supplier", help="Nhà cung cấp vật tư")
    country = fields.Char(string="Country",help="Quốc gia")    
    @api.onchange('supplier')
    def _onchange_supplier(self):
        for rec in self:
            if rec.supplier and rec.supplier.country_id:
                rec.country = rec.supplier.country_id.name
            else:
                rec.country = ''

    price = fields.Float(string="Price", help="Đơn Giá",digits=(16, 3), store=True)  # Thành tiền / Price
    cif_price = fields.Float(string="CIF Price",digits=(16, 3), help="Giá bán cho khách hàng", default=0.0)
    fob_price = fields.Float(string="FOB Price",digits=(16, 3), help="Giá mua vào", default=0.0)
    exwork_price = fields.Float(string="EXW Price", help="Giá xuất xưởng",digits=(16, 3), default=0.0)   