from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError , AccessError
from datetime import timedelta
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)

class ProductCode(models.Model):
    _name = 'product.code'
    _description = 'Style'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "name desc"
    _rec_name = 'name'

    # Thông tin cơ bản
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
                vals['name'] = self.env['ir.sequence'].next_by_code('product.code') or 'New'
        return super(ProductCode, self).create(vals_list)

    # Mở form để tính giá sản phẩm 
    def action_open_price_calculation(self):
        """
        Trả về một hành động để mở form tạo mới cho product.price.calculation.
        """
        self.ensure_one()
        return {
            'name': 'Bảng tính giá sản phẩm',
            'type': 'ir.actions.act_window',
            'res_model': 'product.price.calculation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_code_id': self.id,
                'default_warehouse_order_id': self.warehouse_order_id.id,
            }
        }
        
     
    warehouse_order_id = fields.Many2one('warehouse.order', string="Chương trình", ondelete='cascade')
    color_size_ids = fields.One2many('product.color.size', 'product_code_id', 
        string="Style (Color/Size)", help="Danh sách các Style theo màu và kích thước")
    
    delivery_status = fields.Selection([
        ('not_delivered', 'Chưa xuất'),
        ('partially_delivered', 'Đang xuất'),
        ('fully_delivered', 'Đã xuất đủ'),
    ], string='Trạng thái xuất kho', compute='_compute_delivery_status', store=True, default='not_delivered')
        
    @api.depends('color_size_ids', 'color_size_ids.delivery_status')
    def _compute_delivery_status(self):
        for rec in self:
            if not rec.color_size_ids:
                rec.delivery_status = 'not_delivered'
                continue

            statuses = set(rec.color_size_ids.mapped('delivery_status'))
            if len(statuses) == 1 and 'fully_delivered' in statuses:
                rec.delivery_status = 'fully_delivered'
            elif 'not_delivered' in statuses and len(statuses) == 1:
                rec.delivery_status = 'not_delivered'
            else:
                rec.delivery_status = 'partially_delivered'
                    
    total_style_count = fields.Integer(string='Số lượng style', compute='_compute_total_style_count', store=False)

    @api.depends('color_size_ids')
    def _compute_total_style_count(self):
        for rec in self:
            rec.total_style_count = len(rec.color_size_ids)
            
    price_calculation_ids = fields.One2many('product.price.calculation', 'product_code_id', string='Bảng tính giá')
    
    customer_id = fields.Many2one(
        'customer.cf',
        string="Khách hàng",
        related='warehouse_order_id.customer_id',
        store=True,
        readonly=True,
        create= False
    )   
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
            
    total_order_qty = fields.Integer(
        string="Tổng Order Qty",
        compute="_compute_total_qty",
        store=False
    )
    total_test_qty = fields.Integer(
        string="Tổng Test Qty",
        compute="_compute_total_qty",
        store=False
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Tiền tệ',
        default=lambda self: self.env.ref('base.USD'),
        required=True,
        help="Tiền tệ sử dụng cho giá và số lượng")
    
    ext = fields.Monetary(string="Giá tổng",help='EXT', tracking=True,
        currency_field='currency_id',  default=0, compute="_compute_total_qty",)
    
    @api.depends('color_size_ids.order_qty', 'color_size_ids.test_qty', 'color_size_ids.ext')
    def _compute_total_qty(self):
        for record in self:
            record.total_order_qty = sum(record.color_size_ids.mapped('order_qty'))
            record.total_test_qty = sum(record.color_size_ids.mapped('test_qty'))
            record.ext = sum(record.color_size_ids.mapped('ext'))
            
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
   
     
#-------------------------------------------------------------
# region (**) Tính tổng các vật tư theo Style -----------                 
    # Danh sách vật tư tổng hợp theo Style
    aggregated_material_ids = fields.One2many(
        'warehouse.order.material.line.summary',
        'product_code_id',
        string='Vật tư tổng hợp',
        compute='_compute_grouped_material_line_ids',
        store=True,
    )

    def action_compute_grouped_materials(self):
        for record in self:
            record._compute_grouped_material_line_ids()       

    def _compute_grouped_material_line_ids(self):
        SummaryModel = self.env['warehouse.order.material.line.summary']

        for product in self:
            # Xóa vật tư tổng cũ của product_code này (chỉ xóa các dòng không có color_size_id)
            SummaryModel.search([('product_code_id', '=', product.id), ('color_size_id', '=', False)]).unlink()

            group_dict = {}

            # Gộp từ các style color+size, dữ liệu đã được Odoo tính toán sẵn
            for variant in product.color_size_ids:
                variant._compute_grouped_material_line_ids()
                
                for line in variant.aggregated_material_ids:

                    key = (line.program_customer_line_id.id, line.material_color_id.id, line.dimension)

                    if key not in group_dict:
                        group_dict[key] = {
                            'product_code_id': product.id,
                            'order_id': product.warehouse_order_id.id,
                            'program_customer_line_id': line.program_customer_line_id.id,
                            'material_color_id': line.material_color_id.id,
                            
                            'name': line.name,
                            'mtr_no': line.mtr_no,
                            'mtr_type': line.mtr_type.id if line.mtr_type else False,
                            'mtr_code': line.mtr_code,
                            'mtr_name': line.mtr_name,
                            'rate': line.rate,
                            
                            'dimension': line.dimension,
                            
                            'color_item': line.color_item,
                            'color_code': line.color_code,
                            'color_name': line.color_name,
                            'color_set': line.color_set,
                            
                            'supplier': line.supplier.id if line.supplier else False,
                            'country': line.country,
                            
                            'price': line.price,
                            'cif_price': line.cif_price,
                            'fob_price': line.fob_price,
                            'exwork_price': line.exwork_price,

                            'cons_qty': 0.0,
                        }

                    group_dict[key]['cons_qty'] += line.cons_qty or 0.0

            # Tạo dòng tổng hợp mới cho product_code
            for vals in group_dict.values():
                SummaryModel.create(vals)
            
            # Cập nhật lại aggregated_material_ids
            product.aggregated_material_ids = SummaryModel.search([('product_code_id', '=', product.id), ('color_size_id', '=', False)])

            
    def action_delete_selected_lines(self):
        for rec in self:
            lines_to_delete = rec.color_size_ids.filtered(lambda l: l.x_selected)
            lines_to_delete.unlink()
# endregion
            
#-------------------------------------------------------------
# region (1) PHẦN 1: Tìm kiếm, import/export danh sách vật tư tổng hợp theo Style -----------    
    filtered_aggregated_material_ids = fields.One2many(
        'warehouse.order.material.line.summary',
        string='Tổng vật tư theo Style (đã lọc)',
        compute='_compute_filtered_aggregated_materials',
        store=False,
    )    
    search_text = fields.Char(string='Search')
    search_active = fields.Boolean(string='Search Active', default=False)
    
    # Hàm đếm số lượng vật tư 
    material_count = fields.Integer(
        string="Material Count",
        compute='_compute_material_count',
        store=False
    )

    @api.depends('filtered_aggregated_material_ids')
    def _compute_material_count(self):
        for record in self:
            record.material_count = len(record.filtered_aggregated_material_ids)
            
    # --- Start: Fields for Aggregated Materials Filter ---
    @api.depends('aggregated_material_ids')
    def _compute_agg_available_material_types(self):
        for rec in self:
            rec.agg_available_material_type_ids = [(6, 0, rec.aggregated_material_ids.mapped('mtr_type').ids)]

    @api.depends('aggregated_material_ids')
    def _compute_agg_available_suppliers(self):
        for rec in self:
            rec.agg_available_supplier_ids = [(6, 0, rec.aggregated_material_ids.mapped('supplier').ids)]

    agg_available_material_type_ids = fields.Many2many('material.type', compute='_compute_agg_available_material_types')
    agg_available_supplier_ids = fields.Many2many('supplier.partner', compute='_compute_agg_available_suppliers')

    search_mtr_type = fields.Many2one(
        'material.type',
        string="Lọc theo Loại vật tư (Tổng hợp)",)
    search_supplier = fields.Many2one(
        'supplier.partner',
        string="Nhà cung cấp (Tổng hợp)", )
    # --- End: Fields for Aggregated Materials Filter ---

    def action_apply_search(self):
        self.ensure_one()
        self.search_active = True

    def action_clear_search(self):
        self.ensure_one()
        self.search_active = False
        self.search_text = ''
        self.search_mtr_type = False
        self.search_supplier = False
        
    @api.depends('aggregated_material_ids', 'search_active')
    def _compute_filtered_aggregated_materials(self):
        for order in self:
            if not order.search_active:
                order.filtered_aggregated_material_ids = order.aggregated_material_ids
                continue

            domain = []
            if order.search_mtr_type:
                domain.append(('mtr_type', '=', order.search_mtr_type.id))
            if order.search_supplier:
                domain.append(('supplier', '=', order.search_supplier.id))
            if order.search_text:
                search_text = order.search_text
                domain.extend(['|', '|', ('name', 'ilike', search_text), ('mtr_code', 'ilike', search_text), ('mtr_name', 'ilike', search_text)])
            
            order.filtered_aggregated_material_ids = order.aggregated_material_ids.filtered_domain(domain)   
            
    @api.onchange('search_text')
    def _onchange_search_text(self):
        """Xóa tìm kiếm nếu người dùng xóa nội dung nhập"""
        if not self.search_text and self.search_active:
            self.clear_search()
    
    # import vật tư trong giao diện style
    def action_import_material_style(self):
        self.ensure_one()
        return { 
            'type': 'ir.actions.act_window',
            'name': 'Import Vật Tư',
            'res_model': 'material.style.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_code_id': self.id,  # self là warehouse.order
            },
        }
    
# endregion

 #-------------------------------------------------------------
# region (2) PHẦN 2: Tìm kiếm, import/export danh sách vật tư định mức Style theo color/size -----------    

    filtered_color_size_ids = fields.One2many(
        'product.color.size', 
        string="Danh sách Màu + Size (đã lọc)",
        compute='_compute_filtered_color_size_ids',
        )
    
    search_color_id = fields.Many2one('product.color', string="Lọc theo màu", 
        domain="[('id', 'in', available_color_ids)]")
    search_size_id = fields.Many2one('product.size', string="Lọc theo size",
        domain="[('id', 'in', available_size_ids)]")
    search_code_text= fields.Char(string='Tìm kiếm Style')
    search_code_active= fields.Boolean(string='Tìm kiếm Style', default=False)
    
    available_color_ids = fields.Many2many(
        'product.color', compute='_compute_available_values', )
    available_size_ids = fields.Many2many(
        'product.size', compute='_compute_available_values', )

    @api.depends('color_size_ids')
    def _compute_available_values(self):
        for rec in self:
            rec.available_color_ids = rec.color_size_ids.mapped('color_id').ids
            rec.available_size_ids = rec.color_size_ids.mapped('size_id').ids   
                     
   # Các trường dùng để tìm kiếm trên giao diện 
    @api.depends('color_size_ids', 'search_color_id', 'search_size_id', 'search_code_text')
    def _compute_filtered_color_size_ids(self):
        for order in self:
            # Nếu không có tiêu chí tìm kiếm, hiển thị tất cả vật tư
            if not order.search_code_text and not order.search_color_id and not order.search_size_id:
                order.filtered_color_size_ids = order.color_size_ids
                continue

            # Xây dựng domain (điều kiện) để lọc
            domain = [('id', 'in', order.color_size_ids.ids)]
            
            # Thêm điều kiện lọc theo màu sắc và size nếu được chọn
            if order.search_color_id:
                domain.append(('color_id', '=', order.search_color_id.id))
            if order.search_size_id:
                domain.append(('size_id', '=', order.search_size_id.id))                
            # Thêm điều kiện lọc theo text (tìm trong các trường mtr_no, mtr_name, mtr_code)
            if order.search_code_text:
                search_text = order.search_code_text
                domain.extend([('name', 'ilike', search_text),])
            # Thực hiện tìm kiếm và gán kết quả vào trường hiển thị
            order.filtered_color_size_ids = self.env['product.color.size'].search(domain)  
              
    @api.onchange('search_code_text')
    def _onchange_search_code_text(self):
        """Xóa tìm kiếm nếu người dùng xóa nội dung nhập"""
        if not self.search_code_text and self.search_code_active:
            self.clear_search_code()
   
    def button_dummy(self):
        """Empty method for dropdown toggle button"""
        return True
    
    def action_export_material_product(self):
        """Export thông tin khách hàng và định mức liên quan ra file Excel"""
        self.ensure_one()
        return {
           'type': 'ir.actions.act_url',
            'url': f'/export/material_product/{self.id}',
           'target': 'self',
        }
        
    def action_export_aggregated_product_code(self):
        """Export thông tin khách hàng và tổng danh sách vật tư trong 1 mã hàng liên quan ra file Excel"""
        self.ensure_one()
        return {
           'type': 'ir.actions.act_url',
            'url': f'/export/aggregated_product_code/{self.id}',
           'target': 'self',
        }

    def action_import_style_color_size(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Import Style',
            'res_model': 'style.color.size.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_code_id': self.id,
            },
        }
# endregion  
      
#-------------------------------------------------------------
# region (3) PHẦN 3: Mở các form view Style theo color/size    
        
    def open_product_code_form(self):
        """Mở form view Style product.code theo id"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chi tiết Style',
            'res_model': 'product.code',
            'res_id':  self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('order_management.view_product_code_form').id,
            'target': 'current',
            'flags': {'mode': 'edit'}
        }
    # Mở form chi tiết Style (Color/Size)    
    def open_product_color_size_form(self):
        """Mở form view product.color.size theo id truyền vào"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chi tiết Color/Size',
            'res_model': 'product.color.size',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_code_id': self.id,  # Truyền ID Style vào form mới
            },
        }
        
    # Tạo nhiều Color/Size cùng lúc
    def action_create_style_color_size(self):
        """Mở wizard tạo nhiều Color/Size cùng lúc"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tạo Style Color/Size',
            'res_model': 'create.style.color.size.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_code_id': self.id,  # Truyền ID Style vào form mới
            },
        }
        
    # Tính năng áp dụng Style Color/Size cho các Vật tư
    def action_apply_style_color_size(self):
        """Mở wizard áp dụng Style Color/Size cho các Vật tư"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Áp dụng Style Color/Size',
            'res_model': 'apply.material.style.color.size.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_code_id': self.id,
                'default_warehouse_order_id': self.warehouse_order_id.id,  # Truyền ID Warehouse Order vào form mới
            },
        }
# endregion