from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError , AccessError
from datetime import timedelta
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)

class GarmentStyle(models.Model):
    _name = 'garment.style'
    _description = 'Style'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "name desc"
    _rec_name = 'name'

#-------------------------------------------------------------
# region (1) PHẦN 1: THÔNG TIN CHUNG VỀ STYLE 
    garment_program_id = fields.Many2one('garment.program', string="Chương trình", ondelete='cascade')

    name = fields.Char(string="Style#", required=True, tracking=True,
                       readonly=True, default='New', copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        """
        Ghi đè phương thức create để gán mã theo sequence khi bản ghi được lưu,
        thay vì khi mở form.
        """
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.style') or 'New'
        return super(GarmentStyle, self).create(vals_list)
    
    customer_id = fields.Many2one('customer.garment', string="Khách hàng",
        related='garment_program_id.customer_id',
        store=True,readonly=True, create= False)   
    
    ean_no = fields.Char(string="Mã vạch sản phẩm quốc tế", track_visibility='onchange') 
    ean_no_display = fields.Char(string="Mã vạch sản phẩm quốc tế", track_visibility='onchange', compute='_compute_ean_no_display')
    
    @api.depends('ean_no', 'customer_id.name_customer')
    def _compute_ean_no_display(self):
        for record in self:
            name_parts = []
            if record.ean_no:
                name_parts.append(record.ean_no)
            if record.customer_id and record.customer_id.name_customer:
                name_parts.append(record.customer_id.name_customer)
            record.ean_no_display = ' - '.join(name_parts)
            
    currency_id = fields.Many2one('res.currency',string='Tiền tệ',
        default=lambda self: self.env.ref('base.USD'),required=True,
        help="Tiền tệ sử dụng cho giá và số lượng")
    
    total_order_qty = fields.Integer(
        string="Tổng Order Qty",
    )
    total_test_qty = fields.Integer(
        string="Tổng Test Qty",)    
    
    # Thông tin người tạo
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)  
        return employee.id if employee else False
    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self._get_employee_default(), store=True)
    
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")
    date_create = fields.Datetime(string='Ngày tạo', default=fields.Datetime.now, readonly=True)
    

    image_128 = fields.Image("Image 128", max_width=128, max_height=128, store=True)
    x_selected = fields.Boolean(string="Chọn")   
    
    description_display = fields.Text('Mô tả', compute='_compute_description_display')
    active = fields.Boolean(string='Kích hoạt', default=True)
    description = fields.Text(string='Mô tả', help="Mô tả sản phẩm", track_visibility='onchange')

    @api.depends('description')
    def _compute_description_display(self):
        for record in self:
            if record.description:
                record.description_display = record.description
            else:
                record.description_display = 'Không có mô tả'              
# endregion
#-------------------------------------------------------------
# region (2) PHẦN 2: CHỌN DANH SÁCH VẬT TƯ CHO STYLE

    material_ids = fields.One2many(
        'garment.style.material',
        'style_id',
        string='Danh sách vật tư'
    )
# region (2) PHẦN 2: CHỌN COLORWAY 
    colorway_id = fields.One2many('garment.colorway', 'style_id', string="Colorway", required=True)
  
# endregion  
#-------------------------------------------------------------
# region (3) PHẦN 3: CONSUMPTION
    consumption_line_ids = fields.One2many('garment.consumption', 'style_id', string='Định mức tiêu hao vật tư', help='Danh sách định mức tiêu hao vật tư')
    
    @api.onchange('material_ids')
    def _onchange_material_ids(self):
        if not self.material_ids:
            self.consumption_line_ids = [(5, 0, 0)]
            return

        existing = {
            line.style_material_id.id: line
            for line in self.consumption_line_ids
        }

        new_lines = []

        for mat in self.material_ids:
            if mat.id not in existing:
                new_lines.append((0, 0, {
                    'style_material_id': mat.id,
                    'est_qty': 0.0,
                }))

        self.consumption_line_ids += new_lines

        # xoá consumption nếu material bị xoá
        removed = self.consumption_line_ids.filtered(
            lambda l: l.style_material_id not in self.material_ids
        )
        self.consumption_line_ids -= removed
# endregion 

#-------------------------------------------------------------
# region (4) PHẦN 4: COSTING 
    costing_line_ids = fields.One2many('garment.costing', 'style_id', string='Costing', help='Danh sách Costing')
    
    
# endregion 

#-------------------------------------------------------------
# region (5) PHẦN 5: ORDER BREAKDOWN 
    order_breakdown_line_ids = fields.One2many('garment.order.breakdown', 'style_id', string='Order Breakdown', help='Danh sách Order Breakdown')
    
# endregion 

#-------------------------------------------------------------
# region (6) PHẦN 6: Colorcard 
    colorcard_ids = fields.One2many('garment.colorcard', 'style_id', string='Bảng màu sản phẩm', help='Danh sách bảng màu sản phẩm')     
    
# endregion 