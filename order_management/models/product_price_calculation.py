from odoo import models, fields, api
from odoo.exceptions import ValidationError, AccessError
import re

class ProductPriceCalculation(models.Model):
    _name = 'product.price.calculation'
    _description = 'Bảng tính giá sản phẩm'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "create_date desc"
    _rec_name = 'name'

    name = fields.Char(string="Mã tính giá", compute='_compute_name', store=True)
    product_code_id = fields.Many2one('product.code', string="Style", required=True, 
        domain="[('warehouse_order_id', '=', warehouse_order_id)]",
        ondelete='cascade', tracking=True)
    product_color_size_id = fields.Many2one(
        'product.color.size', 
        string="Style (Color/Size)", 
        required=True, 
        ondelete='cascade', 
        tracking=True,
        domain="[('product_code_id', '=', product_code_id)]"
    )
    warehouse_order_id = fields.Many2one('warehouse.order', string="Chương trình", store=True, required=True)
    customer_id = fields.Many2one(related='warehouse_order_id.customer_id', string="Khách hàng", store=True, readonly=True)
    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.company,)
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', default=lambda self: self.env.ref('base.USD'), required=True)
    
    # Các trường chi phí
    material_cost = fields.Float(string="Material.Cost", help ="Chi phí nguyên phụ liệu", compute='_compute_total_price', store=True, tracking=True)
        
    waste_percent = fields.Integer(string="Waste (%)", help="Phần trăm chi phí hao hụt", tracking=True)
    finance_percent = fields.Integer(string="Finance (%)", help="Phần trăm chi phí tài chính", tracking=True)
    
    waste = fields.Float(string="Waste", compute='_compute_waste_finance', store=True, help="Chi phí hao hụt", tracking=True)
    finance = fields.Float(string="Finance", compute='_compute_waste_finance', store=True, help="Chi phí tài chính", tracking=True)
    
    total_net = fields.Float(string="Total.Net", help="Tổng chi phí nguyên liệu", compute='_compute_total_net', store=True, tracking=True)
    
    cut_make = fields.Float(string="CM", help="Tiền công cắt, may, lắp ráp (CM)", tracking=True)
    
    admin_percent = fields.Integer(string="Admin (%)", help="Phần trăm chi phí quản lý, vận hành (Admin)", tracking=True)
    admin = fields.Float(string="Admin", compute='_compute_admin_cost', store=True, help="Chi phí quản lý, vận hành (Admin)", tracking=True)
    inspection_cost = fields.Float(string="Inspection.Cost", help="Chi phí kiểm hàng", tracking=True)
    test_cost = fields.Float(string="Test.Cost", help="Chi phí kiểm nghiệm", tracking=True)
    import_export_cost = fields.Float(string="Import/Export.Cost", help="Chi phí xuất nhập khẩu", tracking=True)
    
    standard_fob = fields.Float(string="Standard.FOB", help="Giá FOB cơ bản", compute='_compute_standard_fob', store=True, tracking=True)
    
    surcharge_percent = fields.Integer(string="Surcharge (%)", help="Phần trăm chi phí phụ thu", tracking=True)
    surcharge = fields.Float(string="Surcharge", compute='_compute_surcharge', store=True, help="Chi phí phụ thu", tracking=True)
    extra_cost = fields.Float(string="Extra.Cost", help="Chi phí phát sinh khác", tracking=True)
    
    final_fob = fields.Float(string="Final.FOB", help="Giá FOB cuối cùng", compute='_compute_final_fob', store=True, tracking=True)
    agreed_fob = fields.Float(string="Agreed.FOB", help="Giá FOB chốt", tracking=True)
    
    calculation_line_ids = fields.One2many('product.price.calculation.line', 'calculation_id', string="Chi tiết vật tư")
    
    date_calculation = fields.Datetime(string='Ngày tính giá', default=fields.Datetime.now, readonly=True)
    
    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1), 
                                  store=True, readonly=True)
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")

    @api.constrains('waste_percent', 'finance_percent')
    def _check_percent_values(self):
        for record in self:
            if not (0 <= record.waste_percent <= 100):
                raise ValidationError("Tỷ lệ Waste (%) phải nằm trong khoảng từ 0 đến 100.")
            if not (0 <= record.finance_percent <= 100):
                raise ValidationError("Tỷ lệ Finance (%) phải nằm trong khoảng từ 0 đến 100.") 
            if not (0 <= record.admin_percent <= 100):
                raise ValidationError("Tỷ lệ Admin (%) phải nằm trong khoảng từ 0 đến 100.")  
            if not (0 <= record.surcharge_percent <= 100):
                raise ValidationError("Tỷ lệ Surcharge (%) phải nằm trong khoảng từ 0 đến 100.")                
              
    @api.depends('product_code_id', 'product_color_size_id', 'create_date')
    def _compute_name(self):
        for rec in self:
            if rec.product_code_id and rec.product_color_size_id and rec.create_date:
                product_code_name = rec.product_code_id.name
                color_name = rec.product_color_size_id.color_id.name
                size_name = rec.product_color_size_id.size_id.name

                # Convert UTC -> timezone của user
                local_dt = fields.Datetime.context_timestamp(rec, rec.create_date)

                creation_time = local_dt.strftime('%d/%m/%Y %H:%M')
                rec.name = f"{product_code_name} - {color_name}/{size_name} - {creation_time}"
            else:
                rec.name = "Bảng tính giá mới"  

    @api.depends('calculation_line_ids.total_price')
    def _compute_total_price(self):
        for record in self:
            record.material_cost = sum(line.total_price for line in record.calculation_line_ids)
    # tính toán phần trăm hao hụt tài chính       
    @api.depends('material_cost', 'waste_percent', 'finance_percent')
    def _compute_waste_finance(self):
        for rec in self:
            rec.waste = rec.material_cost * (rec.waste_percent / 100.0)
            rec.finance = rec.material_cost * (rec.finance_percent / 100.0)       
             
    # tính toán tổng giá trị cần thanh toán cho khách hàng
    @api.depends('material_cost', 'waste', 'finance')
    def _compute_total_net(self):
        for rec in self:
            rec.total_net = rec.material_cost + rec.waste + rec.finance
            
    # tính toán chi phí quản lý, vận hành (Admin)
    @api.depends('total_net', 'cut_make', 'admin_percent')
    def _compute_admin_cost(self):
        for rec in self:
            rec.admin = (rec.total_net + rec.cut_make) * (rec.admin_percent / 100.0)
            
    @api.depends('total_net', 'cut_make', 'admin', 'inspection_cost', 'test_cost', 'import_export_cost')
    def _compute_standard_fob(self):
        for rec in self:
            rec.standard_fob = (rec.total_net + 
                                rec.cut_make + 
                                rec.admin + 
                                rec.inspection_cost + 
                                rec.test_cost + 
                                rec.import_export_cost)
    # tính toán chi phí phụ thu
    @api.depends('standard_fob', 'surcharge_percent')
    def _compute_surcharge(self):
        for rec in self:
            rec.surcharge = rec.standard_fob * (rec.surcharge_percent / 100.0)

    @api.depends('standard_fob', 'surcharge', 'extra_cost')
    def _compute_final_fob(self):
        for rec in self:
            rec.final_fob = rec.standard_fob + rec.surcharge + rec.extra_cost
            
#-------------------------------------------------------------
# region (1) PPHẦN 1: Tìm kiếm, import/export vật tư theo Style (Color/size) PHẦN tính giá sản phẩm-----------    
    filtered_calculation_line_ids = fields.One2many(
        'product.price.calculation.line',
        string='Danh sách vật tư đặt hàng',
        compute='_compute_filtered_calculation_line',
        inverse='_inverse_filtered_calculation_line')
    def _inverse_filtered_calculation_line(self):
        """
        Cập nhật an toàn danh sách vật tư chính từ view đã lọc,
        bảo toàn các dòng vật tư đang bị ẩn bởi bộ lọc.
        """
        for calculation in self:
            # Kiểm tra xem có bộ lọc nào đang hoạt động không.
            is_filter_active = calculation.search_text or calculation.search_mtr_type or calculation.search_supplier

            # Nếu không có bộ lọc, danh sách hiển thị chính là danh sách đầy đủ.
            # Ta có thể gán trực tiếp, ORM sẽ tự xử lý việc xóa/thêm dòng.
            if not is_filter_active:
                calculation.calculation_line_ids = calculation.filtered_calculation_line_ids
                continue

            # Nếu có bộ lọc, ta phải hợp nhất các thay đổi một cách cẩn thận.
            
            # 1. Chạy lại logic lọc để xác định những dòng nào đã được hiển thị cho người dùng.
            visible_lines = calculation.calculation_line_ids
            if calculation.search_mtr_type:
                visible_lines = visible_lines.filtered(
                    lambda line: line.mtr_type and line.mtr_type.id == calculation.search_mtr_type.id
                )
            if calculation.search_supplier:
                visible_lines = visible_lines.filtered(
                    lambda line: line.supplier and line.supplier.id == calculation.search_supplier.id
                )
            if calculation.search_text:
                search_text = calculation.search_text.lower()
                visible_lines = visible_lines.filtered(
                    lambda line: (search_text in (line.name or '').lower()) or \
                                 (search_text in (line.mtr_code or '').lower())
                )

            # 2. Xác định những dòng đã bị ẩn khỏi tầm nhìn của người dùng.
            hidden_lines = calculation.calculation_line_ids - visible_lines

            # 3. Danh sách đầy đủ mới sẽ là hợp của các dòng bị ẩn và các dòng trong view đã lọc (đã qua chỉnh sửa).
            # Khi gán lại cho trường One2many, Odoo sẽ:
            # - Giữ lại các dòng bị ẩn (hidden_lines).
            # - Giữ lại các dòng đã hiển thị và vẫn còn trong `filtered_calculation_line_ids`.
            # - Xóa các dòng đã hiển thị nhưng bị người dùng xóa khỏi `filtered_calculation_line_ids`.
            # - Tạo các dòng mới được người dùng thêm vào `filtered_calculation_line_ids`.
            calculation.calculation_line_ids = hidden_lines + calculation.filtered_calculation_line_ids
   # Các trường dùng để tìm kiếm trên giao diện
    material_count = fields.Integer(
        string="Material Count",
        compute='_compute_material_count',
        store=False
    )

    @api.depends('filtered_calculation_line_ids')
    def _compute_material_count(self):
        for record in self:
            record.material_count = len(record.filtered_calculation_line_ids)
            
    search_text = fields.Char(string='Tìm kiếm vật tư')
    # --- Start: Fields for Material Norms Filter ---
    @api.depends('calculation_line_ids')
    def _compute_available_material_types(self):
        for rec in self:
            rec.available_material_type_ids = [(6, 0, rec.calculation_line_ids.mapped('mtr_type').ids)]

    @api.depends('calculation_line_ids')
    def _compute_available_suppliers(self):
        for rec in self:
            rec.available_supplier_ids = [(6, 0, rec.calculation_line_ids.mapped('supplier').ids)]
            
    available_supplier_ids = fields.Many2many('supplier.partner', compute='_compute_available_suppliers')
    available_material_type_ids = fields.Many2many('material.type', compute='_compute_available_material_types')    
    
    search_mtr_type = fields.Many2one('material.type', string="Lọc theo Loại vật tư")
    search_supplier = fields.Many2one('supplier.partner', string="Lọc theo Nhà cung cấp")

    @api.depends('search_text', 'search_mtr_type','search_supplier','calculation_line_ids')
    def _compute_filtered_calculation_line(self):
        """
        Lọc danh sách vật tư dựa trên các tiêu chí tìm kiếm.
        Kết quả được gán vào trường 'filtered_calculation_line' và tự động cập nhật trên UI.
        """
        for order in self:
            lines_to_filter = order.calculation_line_ids
            
            # Lọc theo loại vật tư
            if order.search_mtr_type:
                lines_to_filter = lines_to_filter.filtered(
                    lambda line: line.mtr_type and line.mtr_type.id == order.search_mtr_type.id
                )
            
            # Lọc theo nhà cung cấp
            if order.search_supplier:
                lines_to_filter = lines_to_filter.filtered(
                    lambda line: line.supplier and line.supplier.id == order.search_supplier.id
                )
            
            # Lọc theo text
            if order.search_text:
                search_text = order.search_text.lower()
                lines_to_filter = lines_to_filter.filtered(
                    lambda line: (search_text in (line.name or '').lower()) or \
                                 (search_text in (line.mtr_code or '').lower())
                )
            
            order.filtered_calculation_line_ids = lines_to_filter
    
    def action_export_excel(self):
        self.ensure_one()
        return {
           'type': 'ir.actions.act_url',
            'url': f'/export/price_calculation/{self.id}',
           'target': 'self',
        }

    def button_dummy(self):
        """Empty method for dropdown toggle button"""
        return True

# endregion  

    def open_price_calculation_form(self):
        """Mở form view Price Calculation theo id"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tính giá sản phẩm',
            'res_model': 'product.price.calculation',
            'res_id':  self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('order_management.view_product_price_calculation_form').id,
            'target': 'current',
            'flags': {'mode': 'edit'}
        }
        
    # Tạo action xuất mẫu PDF tính giá sản phẩm
    def action_report_price_calculation(self):
        self.ensure_one()
        return self.env.ref('order_management.action_report_price_calculation').report_action(self)    
     
       
class ProductPriceCalculationLine(models.Model):
    _name = 'product.price.calculation.line'
    _description = 'Chi tiết vật tư tính giá'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'
    _order = "mtr_no_prefix asc, mtr_no_suffix asc, mtr_no asc"
    
    
    calculation_id = fields.Many2one('product.price.calculation', string="Bảng tính giá", required=True, ondelete='cascade')
    
    program_customer_id = fields.Many2one('program.customer', string="Vật tư", ondelete='cascade')
    
    # Lấy thông tin vật tư qua related field
    name = fields.Char(string="Mtr#", related='program_customer_id.name', store=True, readonly=True,)  # Mã code vật tư / Mtr No
    
    mtr_no = fields.Char( related='program_customer_id.mtr_no', store=True,
        string="Mtr_no", help='Mã code vật tư', readonly=True,) 
            # sắp xếp vật tư tăng dần theo số thứ tự
    mtr_no_prefix = fields.Char(compute='_compute_mtr_no_parts', string="Mtr No Prefix", store=True)
    mtr_no_suffix = fields.Integer(compute='_compute_mtr_no_parts', string="Mtr No Suffix", store=True)

    @api.depends('mtr_no')
    def _compute_mtr_no_parts(self):
        for rec in self:
            if rec.mtr_no:
                match = re.match(r'([a-zA-Z]*)(\d*)', rec.mtr_no)
                if match:
                    rec.mtr_no_prefix = match.group(1) or ''
                    rec.mtr_no_suffix = int(match.group(2)) if match.group(2) else 0
                else:
                    rec.mtr_no_prefix = rec.mtr_no
                    rec.mtr_no_suffix = 0
            else:
                rec.mtr_no_prefix = ''
                rec.mtr_no_suffix = 0
                
    position = fields.Char(  string="Position", help="Vị trí vật tư",readonly=True,copy=True )
    mtr_type = fields.Many2one(related='program_customer_id.mtr_type',string="Mtr Type", help="Loại vật tư",  ) # Loại vật tư /Type
    mtr_name = fields.Char(related='program_customer_id.mtr_name',  string="Mtr Name", help="Tên vật tư")  # Tên vật tư / Mtr Name
    mtr_code = fields.Char(related='program_customer_id.mtr_code', string='Mtr Code', help='Code item của nhà cung cấp')  # Mã nội bộ / Mtr Code
    rate = fields.Char(related='program_customer_id.rate',string="Unit", help='Ví dụ: mét, cuộn, cái...')
    
    dimension = fields.Char(string="Dimension")
    
    material_color_id = fields.Many2one('material.color', related='program_customer_id.material_color_id', string="Màu vật tư",)
    color_item = fields.Char(string="Color#", help="Mã item màu",related='material_color_id.name', ) # Mã màu vật tư / Color# 
    color_code = fields.Char(string="Color Code", help="Mã code màu",related='material_color_id.color_code', ) # Mã code màu / Color Code 
    color_name = fields.Char(string="Color Name", help="Tên màu",related='material_color_id.color_name', ) # Tên màu /Color Name 
    color_set = fields.Char(string="Color Set", help="Bộ màu",related='material_color_id.color_set_id.name',  )
    
    
    supplier = fields.Many2one('supplier.partner', string="Supplier", related='program_customer_id.supplier', )
    supplier_index = fields.Char(string="Supplier#", related='supplier.supplier_index', help="Mã số nhà cung cấp")
    country = fields.Char(string="Country", related='program_customer_id.country', )
    
    # Lưu lại giá trị tại thời điểm tính toán
    consumption = fields.Float(string="Consumption", )
    contextual_consumption = fields.Char(string="Định mức áp dụng", help="Định mức theo bối cảnh (nếu có)", readonly=False)
    
    price = fields.Float(string="Price",digits=(16, 3), )
    cif_price = fields.Float(string="CIF.Price",digits=(16, 3), help="Giá bán cho khách hàng", default=0.0)
    fob_price = fields.Float(string="FOB.Price",digits=(16, 3), help="Giá mua vào", default=0.0)
    exwork_price = fields.Float(string="EXW.Price",digits=(16, 3), help="Giá xuất xưởng", default=0.0)    
    
    total_price = fields.Float(string="Total",digits=(16, 3), compute='_compute_total_price', store=True)
    total_cif = fields.Float(string="CIF.Total",digits=(16, 3), compute='_compute_total_price', store=True, help="Tổng giá bán cho khách hàng", default=0.0)
    total_fob = fields.Float(string="FOB.Total",digits=(16, 3), compute='_compute_total_price', store=True, help="Tổng giá mua vào", default=0.0)
    total_exwork = fields.Float(string="EXW.Total",digits=(16, 3), compute='_compute_total_price', store=True, help="Tổng giá xuất xưởng", default=0.0)
    
    @api.depends('consumption', 'price', 'cif_price', 'fob_price', 'exwork_price')
    def _compute_total_price(self):
        for line in self:
            line.total_price = (line.consumption or 0.0) * (line.price or 0.0)
            line.total_cif = (line.consumption or 0.0) * (line.cif_price or 0.0)
            line.total_fob = (line.consumption or 0.0) * (line.fob_price or 0.0)
            line.total_exwork = (line.consumption or 0.0) * (line.exwork_price or 0.0)