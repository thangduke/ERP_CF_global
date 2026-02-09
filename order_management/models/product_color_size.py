from odoo import models, fields, api

class ProductColorSize(models.Model):
    _name = 'product.color.size'
    _description = 'Màu + Size trong Style cụ thể'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "product_code_id, color_id, size_id"
    _rec_name = 'display_name'  # <-- thêm dòng này để chỉ định trường hiển thị

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            # Tạo domain để tìm kiếm OR trên các trường được chỉ định
            domain = [('size_id.name', operator, name)]
            domain = ['|', ('color_id.name', operator, name)] + domain
            domain = ['|', ('color', operator, name)] + domain
            domain = ['|', ('description', operator, name)] + domain
            domain = ['|', ('product_code_id.name', operator, name)] + domain
            # Thêm cả trường hiển thị mặc định vào tìm kiếm
            domain = ['|', ('display_name', operator, name)] + domain
            
            # Kết hợp với các điều kiện tìm kiếm có sẵn (nếu có)
            args = domain + args
        
        return self.search(args, limit=limit).name_get()
    
    display_name = fields.Char(string="Tên hiển thị", compute='_compute_display_name', store=True)

    @api.depends('product_code_id', 'color_id', 'size_id')
    def _compute_display_name(self):
        for rec in self:
            parts = [
                rec.product_code_id.name or '',
                rec.color_id.name or '',
                rec.size_id.name or ''
            ]
            rec.display_name = ' - '.join(filter(None, parts)) or 'Không xác định'
            
    product_code_id = fields.Many2one('product.code', string="Style", required=True, ondelete='cascade')
    warehouse_order_id = fields.Many2one('warehouse.order', related='product_code_id.warehouse_order_id',  
                                store=True, string='Chương trình', help='Chương trình liên kết với style này',)
    
    @api.depends('color_size_ids') # <-- Đơn giản hóa dependency
    def _compute_warehouse_order_ids(self):
        """
        Tự động tính toán danh sách chương trình (warehouse_order_ids)
        dựa trên các style (color_size_ids) được chọn.
        """
        for rec in self:
            if rec.color_size_ids:
                # Dùng `mapped` để thu thập các `warehouse.order` duy nhất.
                orders = rec.color_size_ids.mapped('warehouse_order_id')
                rec.warehouse_order_ids = [(6, 0, orders.ids)]
            else:
                # Nếu không có style nào, xóa danh sách chương trình.
                rec.warehouse_order_ids = [(5, 0, 0)] 
    
    customer_id = fields.Many2one(
        'customer.cf',
        string="Khách hàng",
        related='product_code_id.customer_id',
        store=True,
        readonly=True, create= False
    )     
    
    material_ids = fields.Many2many('program.customer',
        'program_customer_product_color_size_rel', 
        'color_size_id',
        'program_customer_id', 
        string="Danh sách vật tư", help="Vật tư định mức cho style này" , tracking=True)
    
    image_128 = fields.Image( string="Mẫu Style", related='product_code_id.image_128', readonly=True)  
    color_id = fields.Many2one('product.color', string="Màu", required=True)
    color = fields.Char(string="Mã màu", help="Mã màu của sản phẩm", related='color_id.color_code', )
  
    size_id = fields.Many2one('product.size', string="Size", required=True)
    ean_no = fields.Char(string="Mã vạch sản phẩm quốc tế", track_visibility='onchange',tracking=True)
    
    label = fields.Char(string="Nhãn", help="Nhãn của sản phẩm")
    dimpk = fields.Float(string="DIMPK", help="Kích thước đóng gói")
    ppk = fields.Integer(string="PPK", help="Số lượng sản phẩm trong mỗi kiện")
    
    order_qty = fields.Integer(string="Order.Qty", help="Số lượng khách đặt hàng", tracking=True)
    test_qty = fields.Integer(string="Test.Qty, Test", help="Số lượng lưu, Test", tracking=True)
    total_qty = fields.Integer(string="Tổng số lượng", compute='_compute_total_qty', store=True, tracking=True)

    @api.depends('order_qty', 'test_qty')
    def _compute_total_qty(self):
        for rec in self:
            rec.total_qty = (rec.order_qty or 0) + (rec.test_qty or 0) 
             
    delivery_status = fields.Selection([
        ('not_delivered', 'Chưa xuất'),
        ('partially_delivered', 'Đang xuất'),
        ('fully_delivered', 'Đã xuất đủ'),
    ], string='Trạng thái xuất kho', store=True, default='not_delivered')


    currency_id = fields.Many2one(
        'res.currency',
        string='Tiền tệ',
        default=lambda self: self.env.ref('base.USD'),
        required=True,
        help="Tiền tệ sử dụng cho giá và số lượng")
    unit_cost = fields.Monetary(string="Đơn giá",help='Unit Cost', tracking=True,
        currency_field='currency_id', default=0)
    ext = fields.Monetary(string="Giá tổng",help='EXT', tracking=True,
        currency_field='currency_id',  default=0, compute='_compute_ext')
    
    @api.depends('order_qty', 'unit_cost')
    def _compute_ext(self):
        for rec in self:
            rec.ext = (rec.order_qty or 0.0) * (rec.unit_cost or 0.0) 
    
    norm_line_ids = fields.One2many(
        'material.norm.line',
        'color_size_id',
        string='Định mức vật tư theo Style',
    )
    aggregated_material_ids = fields.One2many(
        'warehouse.order.material.line.summary',
        'color_size_id',
        string='Vật tư tổng hợp',
        compute='_compute_grouped_material_line_ids',
        store=True,
    )

    def action_compute_grouped_materials(self):
        for record in self:
            record._compute_grouped_material_line_ids()

    def _compute_grouped_material_line_ids(self):
        SummaryModel = self.env['warehouse.order.material.line.summary']

        for variant in self:
            SummaryModel.search([('color_size_id', '=', variant.id)]).unlink()

            qty = (variant.order_qty or 0) + (variant.test_qty or 0)
            group_dict = {}

            for line in variant.material_ids:
                # Lấy định mức theo đúng size của variant
                cons = 0.0
                norm_line = line.norm_line_ids.filtered(lambda n: n.size_id.id == variant.size_id.id and n.color_size_id.id == variant.id)
                if norm_line:
                    cons = norm_line[0].consumption or 0.0

                # Lấy dimension và giá trực tiếp từ program.customer
                dimension = line.dimension or ''
                price = line.price or 0.0
                cif_price = line.cif_price or 0.0
                fob_price = line.fob_price or 0.0
                exwork_price = line.exwork_price or 0.0
                    
                # có cùng vật tư cơ sở, cùng màu vật tư VÀ cùng kích thước.
                key = (line.program_customer_line_id.id, line.material_color_id.id , dimension)

                if key not in group_dict:
                    group_dict[key] = {
                        'color_size_id': variant.id,
                        'product_code_id': variant.product_code_id.id,
                        'order_id': variant.warehouse_order_id.id,
                        'program_customer_line_id': line.program_customer_line_id.id,
                        'material_color_id': line.material_color_id.id,
                        
                        'name': line.name,
                        'mtr_no': line.mtr_no,
                        'mtr_type': line.mtr_type.id if line.mtr_type else False,
                        'mtr_code': line.mtr_code,
                        'mtr_name': line.mtr_name,
                        'rate': line.rate,
                        
                        'dimension': dimension,
                        
                        'color_item': line.color_item,
                        'color_code': line.color_code,
                        'color_name': line.color_name,
                        'color_set': line.color_set,
                        
                        'supplier': line.supplier.id if line.supplier else False,
                        'country': line.country,
                        
                        'price': price,
                        'cif_price': cif_price,
                        'fob_price': fob_price,
                        'exwork_price': exwork_price,
                        'cons_qty': 0.0,
                    }

                group_dict[key]['cons_qty'] += cons * qty
            
            # Lọc và tạo các dòng summary mới, chỉ tạo nếu cons_qty > 0
            vals_to_create = [vals for vals in group_dict.values() if vals.get('cons_qty')]
            if vals_to_create:
                SummaryModel.create(vals_to_create)
            # Dòng gán "variant.aggregated_material_ids = ..." đã được xóa vì Odoo sẽ tự xử lý
                 
    _sql_constraints = [
        ('unique_variant', 'unique(product_code_id, color_id, size_id)', 
         'Mỗi Style chỉ được có một dòng cho mỗi Màu + Size.')
    ]
    
    # Thông tin người tạo
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)  
        return employee.id if employee else False
    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self._get_employee_default(), store=True)
    
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")
    
    date_create = fields.Datetime(string='Ngày tạo', default=fields.Datetime.now, readonly=True)
    
    description = fields.Text(string='Mô tả', related='product_code_id.description', store=True, 
        help="Mô tả sản phẩm", track_visibility='onchange',tracking=True)
    description_display = fields.Text('Mô tả', compute='_compute_description_display')   
    @api.depends('description')
    def _compute_description_display(self):
        for record in self:
            if record.description:
                record.description_display = record.description
            else:
                record.description_display = 'Không có mô tả'
                

              
#-------------------------------------------------------------
# region (1) PPHẦN 1: Tìm kiếm, import/export vật tư tổng theo Style (Color/size) -----------    
    filtered_aggregated_material_ids = fields.One2many(
        'warehouse.order.material.line.summary',
        string='Tổng vật tư theo Style (đã lọc)',
        compute='_compute_filtered_aggregated_materials',
        store=False,
    )    
    search_text = fields.Char(string='Search')
    search_active = fields.Boolean(string='Search Active', default=False)


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
                domain.extend(['|', ('name', 'ilike', search_text), ('mtr_code', 'ilike', search_text)])
            
            order.filtered_aggregated_material_ids = order.aggregated_material_ids.filtered_domain(domain)
            
    @api.onchange('search_text')
    def _onchange_search_text(self):
        """Xóa tìm kiếm nếu người dùng xóa nội dung nhập"""
        if not self.search_text and self.search_active:
            self.action_clear_search()
    
    def action_export_aggregated_material(self):
        """Export thông tin vật tư tổng hợp theo Style (Color/Size) ra file Excel"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/export/aggregated_product_color_size/{self.id}',
            'target': 'self',
        }
# endregion            


# region (2) PHẦN 2: Tìm kiếm, import/export vật tư định mức theo Style (Color/size) ----------- 
    # Danh sách vật tư đã được lọc để hiển thị
    filtered_material_line = fields.Many2many(
        'program.customer',
        string='Danh sách vật tư đặt hàng',
        compute='_compute_filtered_material_line',
        inverse='_inverse_filtered_material_line',
        help="Đây là danh sách vật tư được lọc từ danh sách chính."
    )
       
    def _inverse_filtered_material_line(self):
        for rec in self:
            is_filter_active = rec.material_search_text or rec.norm_search_mtr_type or rec.norm_search_supplier

            # Nếu không có bộ lọc nào đang hoạt động, danh sách hiển thị là danh sách đầy đủ.
            # Chúng ta có thể ghi đè trực tiếp.
            if not is_filter_active:
                rec.material_ids = [(6, 0, rec.filtered_material_line.ids)]
                continue

            # Nếu có bộ lọc, chúng ta cần hợp nhất các thay đổi một cách cẩn thận.
            # 1. Xây dựng lại domain để tìm các mục đã được hiển thị cho người dùng.
            domain_for_shown_items = [('id', 'in', rec.material_ids.ids)]
            if rec.norm_search_mtr_type:
                domain_for_shown_items.append(('mtr_type', '=', rec.norm_search_mtr_type.id))
            if rec.norm_search_supplier:
                domain_for_shown_items.append(('supplier', '=', rec.norm_search_supplier.id))
            if rec.material_search_text:
                search_text = rec.material_search_text
                domain_for_shown_items.extend(['|',
                    ('mtr_no', 'ilike', search_text),
                    ('mtr_code', 'ilike', search_text),
                ])
            
            shown_item_ids = self.env['program.customer'].search(domain_for_shown_items).ids

            # 2. Các mục bị ẩn là các mục trong danh sách gốc trừ đi các mục đã hiển thị.
            hidden_item_ids = set(rec.material_ids.ids) - set(shown_item_ids)
            
            # 3. Các mục người dùng muốn giữ lại từ chế độ xem đã lọc.
            visible_items_to_keep_ids = set(rec.filtered_material_line.ids)
            
            # 4. Danh sách đầy đủ mới là hợp của các mục bị ẩn và các mục được giữ lại.
            new_material_ids = list(hidden_item_ids | visible_items_to_keep_ids)
            
            rec.material_ids = [(6, 0, new_material_ids)]
                       
   # Các trường dùng để tìm kiếm trên giao diện
    material_search_text = fields.Char(string='Tìm kiếm vật tư')
    material_search_active = fields.Boolean(string='Đang tìm vật tư', default=False)
    
    material_count_line = fields.Integer(
        string="Material Count",
        compute='_compute_material_count_line',
        store=False
    )

    @api.depends('filtered_material_line')
    def _compute_material_count_line(self):
        for record in self:
            record.material_count_line = len(record.filtered_material_line)
            
    # --- Start: Fields for Material Norms Filter ---
    @api.depends('material_ids')
    def _compute_norm_available_material_types(self):
        for rec in self:
            rec.norm_available_material_type_ids = [(6, 0, rec.material_ids.mapped('mtr_type').ids)]

    @api.depends('material_ids')
    def _compute_norm_available_suppliers(self):
        for rec in self:
            rec.norm_available_supplier_ids = [(6, 0, rec.material_ids.mapped('supplier').ids)]

    norm_available_material_type_ids = fields.Many2many('material.type', compute='_compute_norm_available_material_types')
    norm_available_supplier_ids = fields.Many2many('supplier.partner', compute='_compute_norm_available_suppliers')
    
    norm_search_mtr_type = fields.Many2one(
        'material.type',
        string="Lọc theo Loại vật tư (Định mức)",)
    norm_search_supplier = fields.Many2one(
        'supplier.partner',
        string="Nhà cung cấp (Định mức)",)

    # --- End: Fields for Material Norms Filter ---
    
    @api.depends('material_search_text', 'norm_search_mtr_type', 'material_ids', 'norm_search_supplier')
    def _compute_filtered_material_line(self):
        for record in self:
            # Nếu không có tiêu chí tìm kiếm, hiển thị tất cả vật tư
            if not record.material_search_text and not record.norm_search_mtr_type and not record.norm_search_supplier:
                record.filtered_material_line = record.material_ids
                continue
            # Xây dựng domain (điều kiện) để lọc
            domain = [('id', 'in', record.material_ids.ids)]
            # Thêm điều kiện lọc theo loại vật tư nếu được chọn
            if record.norm_search_mtr_type:
                domain.append(('mtr_type', '=', record.norm_search_mtr_type.id))
            # Thêm điều kiện lọc theo nhà cung cấp nếu được chọn
            if record.norm_search_supplier:
                domain.append(('supplier', '=', record.norm_search_supplier.id))
                
            # Thêm điều kiện lọc theo text (tìm trong các trường mtr_no, mtr_name, mtr_code)
            if record.material_search_text:
                search_text = record.material_search_text
                domain.extend(['|',
                    ('mtr_no', 'ilike', search_text),
                    ('mtr_code', 'ilike', search_text),
                ])
            
            # Thực hiện tìm kiếm và gán kết quả vào trường hiển thị
            record.filtered_material_line = self.env['program.customer'].search(domain)
            

    @api.onchange('material_search_text')
    def _onchange_material_search_text(self):
        '''Xóa tìm kiếm nếu người dùng xóa nội dung nhập'''
        if not self.material_search_text and self.material_search_active:
            self.clear_search_material()
           
    #### Các phương thức khác ####      
    def button_dummy(self):
        """Empty method for dropdown toggle button"""
        return True
    
    def action_export(self):
        """Export thông tin khách hàng và định mức liên quan ra file Excel"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/export/product/{self.id}',
            'target': 'self',
        }
    
# endregion            

    # Mở form chi tiết Style (Color/Size)
    def open_product_color_size_form(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chi tiết màu & size',
            'res_model': 'product.color.size',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('order_management.view_product_color_size_form').id,
            'target': 'current',
            'flags': {'mode': 'edit'}
        }