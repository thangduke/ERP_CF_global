from odoo import models, fields, api
from odoo.exceptions import ValidationError, AccessError
import re

class MaterialDimension(models.Model):
    _name = 'material.dimension'
    _description = 'Kích thước vật tư'
    _order = 'name'

    name = fields.Char(string='Dimension', required=True, index=True)
    description = fields.Char(string='Mô tả', help='Mô tả chi tiết về kích thước')
    
    @api.constrains('name')
    def _check_unique_name(self):
        for rec in self:
            if rec.name:
                # Case-insensitive search
                existing = self.search([('name', '=ilike', rec.name), ('id', '!=', rec.id)])
                if existing:
                    raise ValidationError(f"Dimension '{rec.name}' đã tồn tại.")

class MaterialRate(models.Model):
    _name = 'material.rate'
    _description = 'Đơn vị tính vật tư'
    _order = 'name'

    name = fields.Char(string='Unit', required=True, index=True)
    description = fields.Char(string='Mô tả', help='Mô tả chi tiết về kích thước')
    active = fields.Boolean(string='Active', default=True)
    
    @api.constrains('name')
    def _check_unique_name(self):
        for rec in self:
            if rec.name:
                # Case-insensitive search
                existing = self.search([('name', '=ilike', rec.name), ('id', '!=', rec.id)])
                if existing:
                    raise ValidationError(f"Đơn vị tính (Unit) '{rec.name}' đã tồn tại.")

class ProgramCustomer(models.Model):
    _name = 'program.customer'
    _description = 'Danh sách vật tư'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'
    _order = "mtr_no_sort_key asc, mtr_no asc"
    _rec_name = 'name'

    @api.constrains('program_customer_line_id', 'material_color_id', 'supplier', 'dimension_id')
    def _check_unique_combination(self):
        for rec in self:
            domain = [
                ('id', '!=', rec.id),
                ('program_customer_line_id', '=', rec.program_customer_line_id.id),
            ]
            
            if rec.material_color_id:
                domain.append(('material_color_id', '=', rec.material_color_id.id))
            else:
                domain.append(('material_color_id', '=', False))
                
            if rec.supplier:
                domain.append(('supplier', '=', rec.supplier.id))
            else:
                domain.append(('supplier', '=', False))

            if rec.dimension_id:
                domain.append(('dimension_id', '=', rec.dimension_id.id))
            else:
                domain.append(('dimension_id', '=', False))

            if self.search_count(domain) > 0:
                # Build a more descriptive error message
                error_parts = [
                    f"Vật tư: {rec.program_customer_line_id.name_display or '(Trống)'}",
                    f"Màu vật tư: {rec.material_color_id.name or '(Trống)'}",
                    f"Nhà cung cấp: {rec.supplier.name_supplier or '(Trống)'}",
                    f"Kích thước: {rec.dimension_id.name or '(Trống)'}"
                ]
                error_message = "Đã tồn tại một vật tư với sự kết hợp sau:\n- " + "\n- ".join(error_parts)
                raise ValidationError(error_message)
    
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            # Tạo domain để tìm kiếm OR trên các trường được chỉ định
            domain = [('supplier', operator, name)]
            # Lưu ý: `mtr_name` được sử dụng thay vì `name` hoặc `mtr_code` theo yêu cầu của bạn
            domain = ['|', ('mtr_code', operator, name)] + domain
            domain = ['|', ('mtr_no', operator, name)] + domain
            domain = ['|', ('mtr_type', operator, name)] + domain
            domain = ['|', ('position', operator, name)] + domain
            # Kết hợp (AND) domain tìm kiếm với các args mặc định
            args = args + domain
        return self.search(args, limit=limit).name_get()

    # Đã chuyển từ Many2one sang Many2many
    warehouse_order_ids = fields.Many2many('warehouse.order', 
        'program_customer_warehouse_order_rel', 
        'program_customer_id', 
        'warehouse_order_id', 
        string='Chương trình',
        compute='_compute_warehouse_order_ids',
        store=True)   
     
    color_size_ids = fields.Many2many('product.color.size', 
        'program_customer_product_color_size_rel', 
        'program_customer_id',
        'color_size_id', 
        string="Các Style (Color/Size)")
    
    @api.depends('color_size_ids')
    def _compute_warehouse_order_ids(self):
        """
        Tự động tính toán warehouse_order_ids dựa trên color_size_ids đã chọn.
        """
        for rec in self:
            if rec.color_size_ids:
                # Lấy tất cả các warehouse_order_id duy nhất từ các color_size_ids đã chọn
                warehouse_orders = rec.color_size_ids.mapped('warehouse_order_id')
                # Cập nhật lại trường warehouse_order_ids
                rec.warehouse_order_ids = [(6, 0, warehouse_orders.ids)]
            else:
                # Nếu không có color_size_ids nào được chọn, làm rỗng warehouse_order_ids
                rec.warehouse_order_ids = [(6, 0, [])]
    
    
    program_customer_line_id = fields.Many2one('program.customer.line', string='Vật tư gốc', ondelete='cascade', required=True, )

    name = fields.Char(string="Mtr#", help='Mã code định mức', compute='_compute_name', readonly=True,  store=True)  # Mtr#
    
    @api.depends('mtr_no', 'color_item', 'dimension')
    def _compute_name(self):
        for rec in self:
            parts = [
                rec.mtr_no or '',
                rec.color_item or '',
                rec.dimension or ''
            ]
            rec.name = '.'.join(filter(None, parts))
       
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            # Mở rộng tìm kiếm để bao gồm cả trường 'name' (Mtr#)
            domain = ['|', ('name', 'ilike', name)]
            domain = ['|', ('mtr_no', 'ilike', name)] + domain
            domain = ['|', ('mtr_code', 'ilike', name)] + domain
            domain = ['|', ('mtr_name', 'ilike', name)] + domain
            domain = ['|', ('position', 'ilike', name)] + domain
            domain = ['|', ('supplier', 'ilike', name)] + domain
            
            # Lấy mtr_type_ids nếu có
            mtr_type_ids = self.env['material.type'].search([('name', 'ilike', name)]).ids
            if mtr_type_ids:
                domain = ['|', ('mtr_type', 'in', mtr_type_ids)] + domain

            args = domain + (args or [])
        
        return self.search(args, limit=limit).name_get()
            
    # Trường hiển thị phụ từ liên kết
    mtr_no = fields.Char( related='program_customer_line_id.name_display', store=True, 
        string="Mtr_no", help='Mã code vật tư', readonly=True,) 
            # sắp xếp vật tư tăng dần theo số thứ tự
    mtr_no_sort_key = fields.Integer(compute='_compute_mtr_no_sort_key',
        string="Sort Key for Mtr No", store=True, index=True)
    @api.depends('mtr_no')
    def _compute_mtr_no_sort_key(self):
        for rec in self:
            if rec.mtr_no:
                # Tách phần số từ chuỗi (VD: AC0003 -> 3, FB12 -> 12)
                numeric_part = re.findall(r'\d+', rec.mtr_no)
                rec.mtr_no_sort_key = int(numeric_part[0]) if numeric_part else 0
            else:
                rec.mtr_no_sort_key = 0                          
    
    mtr_type = fields.Many2one(related='program_customer_line_id.mtr_type',string="Mtr Type", help="Loại vật tư",  store=True) # Loại vật tư /Type
    mtr_name = fields.Char(related='program_customer_line_id.mtr_name', store=True, string="Mtr Name", help="Tên vật tư")  # Tên vật tư / Mtr Name
    mtr_code = fields.Char(related='program_customer_line_id.mtr_code', store=True, string='Mtr Code', help='Code item của nhà cung cấp')  # Mã nội bộ / Mtr Code
    rate = fields.Char(related='program_customer_line_id.rate', store=True , string="Unit", help='Ví dụ: mét, cuộn, cái...')
    
   #* Màu sắc vật tư
    material_color_id = fields.Many2one('material.color', string='Màu vật tư', help='Màu sắc của vật tư', required=True)
    color_item = fields.Char(string="Color#", help="Mã item màu",related='material_color_id.name', store=True) # Mã màu vật tư / Color# 
    color_code = fields.Char(string="Color Code", help="Mã code màu",related='material_color_id.color_code', store=True) # Mã code màu / Color Code 
    color_name = fields.Char(string="Color Name", help="Tên màu",related='material_color_id.color_name', store=True) # Tên màu /Color Name 
    color_set = fields.Char(string="Color Set", help="Bộ màu",related='material_color_id.color_set_id.name', store=True ) # Bộ màu (nếu có)/ Color Set 
    
    
    # * Dimension theo vật tư, Size
    dimension = fields.Char(string="Dimension", related='dimension_id.name', store=True, help="Kích thước theo ngữ cảnh")
    
    dimension_id = fields.Many2one('material.dimension', string="Dimension", help="Kích thước theo ngữ cảnh")

    #* Định mức vật tư theo style(Color,Size) và vật tư
    norm_line_ids = fields.One2many(
        'material.norm.line', 'program_customer_id',
        string='Tất cả định mức vật tư', 
    )

    norm_line_style_ids = fields.One2many(
        'material.norm.line', 'program_customer_id',
        string="Định mức vật tư theo Style",
        compute='_compute_norm_line_style_ids',
        inverse='_inverse_norm_line_style_ids'
    )

    @api.depends('norm_line_ids', 'contextual_color_size_id')
    def _compute_norm_line_style_ids(self):
        for rec in self:
            if rec.contextual_color_size_id:
                rec.norm_line_style_ids = rec.norm_line_ids.filtered(
                    lambda l: l.color_size_id == rec.contextual_color_size_id
                )
            else:
                rec.norm_line_style_ids = self.env['material.norm.line']

    def _inverse_norm_line_style_ids(self):
        for rec in self:
            # Lấy các dòng định mức không thuộc về style đang xem trong ngữ cảnh
            other_style_lines = rec.norm_line_ids.filtered(
                lambda l: l.color_size_id != rec.contextual_color_size_id
            )

            # Gán color_size_id cho các dòng mới được tạo từ giao diện (những dòng chưa có)
            # để đảm bảo chúng được liên kết đúng với style hiện tại.
            for line in rec.norm_line_style_ids:
                if not line.color_size_id and rec.contextual_color_size_id:
                    line.color_size_id = rec.contextual_color_size_id

            # Cập nhật lại toàn bộ danh sách `norm_line_ids` bằng cách kết hợp
            # các dòng của style khác và các dòng (mới/đã sửa) của style hiện tại.
            # Odoo sẽ tự động phát hiện các thay đổi (tạo mới, sửa, xóa) và lưu vào database.
            rec.norm_line_ids = other_style_lines + rec.norm_line_style_ids
            
    position = fields.Char(
        string="Position", 
        compute='_compute_contextual_data', 
        store=False, # QUAN TRỌNG: Phải là store=False vì phụ thuộc vào ngữ cảnh
        help="Vị trí vật tư. Giá trị này phụ thuộc vào Style đang xem."
    )
    consumption = fields.Float(
        string="Consumption", 
        compute='_compute_contextual_data', 
        store=False, # QUAN TRỌNG: Phải là store=False vì phụ thuộc vào ngữ cảnh
        digits=(16, 3), 
        help="Định mức theo ngữ cảnh. Giá trị này phụ thuộc vào Style đang xem."
    )
    
    contextual_warehouse_order_id = fields.Many2one(
        'warehouse.order',
        string='Chương trình (Ngữ cảnh)',
        compute='_compute_contextual_data',
        store=False, # QUAN TRỌNG: Phải là store=False vì phụ thuộc vào ngữ cảnh
        help="Chương trình được xác định từ Style (Color/Size) đang xem."
    )
    contextual_color_size_id = fields.Many2one(
        'product.color.size',
        string='Style (Ngữ cảnh)',
        compute='_compute_contextual_data',
        store=False, # QUAN TRỌNG: Phải là store=False vì phụ thuộc vào ngữ cảnh
        help="Style (Color/Size) đang được xem trong ngữ cảnh."
    )
    
    @api.depends('norm_line_ids.consumption', 'norm_line_ids.position', 'norm_line_ids.size_id', 'norm_line_ids.color_size_id')
    @api.depends_context('active_id', 'active_model')
    def _compute_contextual_data(self):
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        # Chỉ cần logic dựa trên context là đủ
        if active_model == 'product.color.size' and active_id:
            color_size_record = self.env['product.color.size'].browse(active_id).exists()
            if color_size_record:
                current_size_id = color_size_record.size_id.id
                for rec in self:
                    # Tìm dòng định mức tương ứng
                    norm_line = rec.norm_line_ids.filtered(
                        lambda l: l.size_id.id == current_size_id and l.color_size_id.id == active_id
                    )
                    # Gán giá trị
                    rec.consumption = norm_line.consumption if norm_line else 0.0
                    rec.position = norm_line.position if norm_line else ''
                    rec.contextual_warehouse_order_id = color_size_record.warehouse_order_id
                    rec.contextual_color_size_id = color_size_record
                return # Kết thúc

        # Nếu không tìm được context, gán giá trị mặc định
        for rec in self:
            rec.consumption = 0
            rec.position = ''
            rec.contextual_warehouse_order_id = False
            rec.contextual_color_size_id = False

    # Trường compute để hiển thị các định mức trên 1 dòng
    contextual_consumption = fields.Char(
        string="Định mức áp dụng",
        compute='_compute_contextual_consumption',
        help="Hiển thị định mức vật tư theo định dạng 'Size: Value' dựa trên Style (color/size) đang được xem."
    )

    @api.depends('norm_line_ids.consumption', 'norm_line_ids.size_id', 'norm_line_ids.color_size_id')
    def _compute_contextual_consumption(self):
        """
        Tự động tính định mức dựa trên context (đang xem từ Style nào)
        và dữ liệu trong norm_line_ids.
        """
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')

        for rec in self:
            rec.contextual_consumption = ""

            # Chỉ xử lý khi đang xem từ product.color.size
            if active_model == 'product.color.size' and active_id:
                color_size_record = self.env['product.color.size'].browse(active_id)
                if not color_size_record.exists() or not color_size_record.size_id:
                    continue

                current_size_id = color_size_record.size_id.id
                size_name = color_size_record.size_id.name

                # Tìm định mức theo Style + Size
                matching_norm = rec.norm_line_ids.filtered(
                    lambda line: line.color_size_id.id == color_size_record.id
                    and line.size_id.id == current_size_id
                )
                if matching_norm:
                    rec.contextual_consumption = f"{size_name}: {matching_norm[0].consumption}"
          
    # Price/FOB Price/EXW Price/
    price = fields.Float(string="Price", digits=(16, 3), help="Đơn Giá")
    cif_price = fields.Float(string="CIF.Price", digits=(16, 3), help="Giá CIF")
    fob_price = fields.Float(string="FOB.Price", digits=(16, 3), help="Giá FOB")
    exwork_price = fields.Float(string="EXW.Price", digits=(16, 3), help="Giá EXW")
    
    total = fields.Float(string="Total", compute='_compute_totals', digits=(16, 3), help="Tổng giá trị theo ngữ cảnh")
    cif_total = fields.Float(string="CIF.Total", compute='_compute_totals', digits=(16, 3), help="Tổng CIF theo ngữ cảnh")
    fob_total = fields.Float(string="FOB.Total", compute='_compute_totals', digits=(16, 3), help="Tổng FOB theo ngữ cảnh")
    exwork_total = fields.Float(string="EXW.Total", compute='_compute_totals', digits=(16, 3), help="Tổng EXW theo ngữ cảnh")             

    @api.depends('consumption', 'price', 'cif_price', 'fob_price', 'exwork_price')
    def _compute_totals(self):
        for rec in self:
            rec.total = rec.consumption * rec.price
            rec.cif_total = rec.consumption * rec.cif_price
            rec.fob_total = rec.consumption * rec.fob_price
            rec.exwork_total = rec.consumption * rec.exwork_price
            
    
    # * Chọn NCC theo vật tư        
    supplier = fields.Many2one('supplier.partner', string="Supplier", help="Nhà cung cấp vật tư")
    supplier_index = fields.Char(string="Supplier#", help="Mã số nhà cung cấp", related='supplier.supplier_index', store=True)
    
    country = fields.Char(string="Country",help="Quốc gia")    
    @api.onchange('supplier')
    def _onchange_supplier(self):
        for rec in self:
            if rec.supplier and rec.supplier.country_id:
                rec.country = rec.supplier.country_id.name
            else:
                rec.country = ''

    x_selected = fields.Boolean(string="Chọn", default=False)
    
    def action_delete_all_lines(self):
        """
        Xóa các bản ghi trong recordset hiện tại.
        Phương thức này được gọi từ một nút bấm trên giao diện người dùng.
        """
        self.unlink()
            
    # Mở form chi tiết vật tư
    def open_material_form(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chi tiết vật tư',
            'res_model': 'program.customer',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('order_management.view_program_customer_form').id,
            'target': 'new',
            'flags': {'mode': 'edit'}
        } 
    
          
                 
# Tạo model trung gian tổng hợp vật tư     
class WarehouseOrderMaterialLineSummary(models.TransientModel):
    _name = 'warehouse.order.material.line.summary'
    _description = 'Tổng hợp vật tư theo chương trình (tạm thời)'
    _order = 'name asc' 
    _rec_name = 'name'

    order_id = fields.Many2one('warehouse.order', string='Chương trình')
    product_code_id = fields.Many2one('product.code', string='Mã sản phẩm')
    color_size_id = fields.Many2one('product.color.size', string="Style (Màu/Size)")
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **kwargs):
        records = self.search(domain or [], order=order)
        if not records:
            return []

        def sort_key(record):
            if record.name:
                # Tách phần chữ và số ra
                match = re.match(r'([A-Za-z]+)(\d+)', record.name)
                if match:
                    prefix = match.group(1)  # phần chữ (AC, FB, ZI...)
                    number = int(match.group(2))  # phần số (1, 2, 3, 4...)
                    return (prefix, number)
                return (record.name, 0)
            return ('', 0)

        sorted_records = sorted(records, key=sort_key)

        if limit:
            paginated_records = sorted_records[offset:offset + limit]
        else:
            paginated_records = sorted_records[offset:]

        if not paginated_records:
            return []

        return self.browse([r.id for r in paginated_records]).read(fields)
    
    # >> Khóa gộp vật tư
    program_customer_line_id = fields.Many2one('program.customer.line', string="Vật tư gốc")
    material_color_id = fields.Many2one('material.color', string="Màu vật tư")
    # >> Thông tin mô tả vật tư
    name = fields.Char(string='Mtr#', help='Mã code vật tư')
    mtr_no = fields.Char(string='Mtr_no', help='Mã code vật tư')  # Mã vật tư / Mtr No
    position = fields.Char(string="Position", help="Vị trí vật tư")
    mtr_type = fields.Many2one('material.type', string="Mtr Type", help="Loại vật tư",)
    mtr_code = fields.Char(string='Mtr Code', help='Code item của nhà cung cấp')
    mtr_name = fields.Char(string="Mtr Name", help="Tên vật tư")
    rate = fields.Char(string="Unit", help='Ví dụ: mét, cuộn, cái...')
    # >> Kích thước
    dimension = fields.Char(string='Dimension', help="Kích thước vật tư", default=' ')

    # >> Màu sắc
    color_item = fields.Char(string="Color Item", help="Mã item màu",)
    color_code = fields.Char(string="Color Code", help="Mã code màu")
    color_name = fields.Char(string="Color Name", help="Tên màu")
    color_set = fields.Char(string="Color Set", help="Bộ màu")
    
    # >> Thông tin nhà cung cấp
    supplier = fields.Many2one('supplier.partner', string="Supplier", help="Nhà cung cấp")
    supplier_index = fields.Char(string="Supplier#", related='supplier.supplier_index', help="Mã số nhà cung cấp")
    
    country = fields.Char(string="Quốc gia", help=" Quốc gia nhà cung cấp")
    
    # >> Định lượng và giá
    cons_qty = fields.Float(string='Cons.Qty', digits=(16, 3), help='Số lượng định mức') 
    
    # Price/FOB Price/EXW Price/
    price = fields.Float(string="Price",  digits=(16, 3),)
    cif_price = fields.Float(string="CIF.Price", digits=(16, 3),)
    fob_price = fields.Float(string="CIF.Price",  digits=(16, 3), )
    exwork_price = fields.Float(string="EXW.Price", digits=(16, 3), )
    
    # >> Tổng thành tiền
    total = fields.Float(string="Total", compute="_compute_total", digits=(16, 3), )
    cif_total = fields.Float(string="CIF.Total", compute="_compute_total", digits=(16, 3),)
    fob_total = fields.Float(string="FOB.Total", compute="_compute_total", digits=(16, 3),)
    exwork_total = fields.Float(string="EXW.Total", compute="_compute_total", digits=(16, 3),)

    @api.depends('cons_qty', 'price', 'cif_price', 'fob_price', 'exwork_price')
    def _compute_total(self):
        for rec in self:
            rec.total = (rec.cons_qty or 0.0) * (rec.price or 0.0)
            rec.cif_total = (rec.cons_qty or 0.0) * (rec.cif_price or 0.0)
            rec.fob_total = (rec.cons_qty or 0.0) * (rec.fob_price or 0.0)
            rec.exwork_total = (rec.cons_qty or 0.0) * (rec.exwork_price or 0.0)
            
            
