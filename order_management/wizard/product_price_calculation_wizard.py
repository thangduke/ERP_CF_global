# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ProductPriceCalculationWizard(models.TransientModel):
    _name = 'product.price.calculation.wizard'
    _description = 'Wizard Tính Giá Sản Phẩm'

    # ==== Thông tin chung ====
    name = fields.Char(string="Mã tính giá", compute='_compute_name', )
    @api.depends('warehouse_order_id', 'product_color_size_id')
    def _compute_name(self):
        for rec in self:
            if rec.warehouse_order_id and rec.product_color_size_id:
                rec.name = f"{rec.warehouse_order_id.name}-{rec.product_color_size_id.name}"
            else:
                rec.name = "New"    
    warehouse_order_id = fields.Many2one('warehouse.order', string="Chương trình",  required=True)
    customer_id = fields.Many2one(related='warehouse_order_id.customer_id', string="Khách hàng",  readonly=True)
    product_code_id = fields.Many2one(
        'product.code', 
        string="Style", 
        required=True, 
        domain="[('warehouse_order_id', '=', warehouse_order_id)]",
        ondelete='cascade', tracking=True
    )
    product_color_size_id = fields.Many2one(
        'product.color.size', 
        string="Style (Color/Size)", 
        required=True, 
        ondelete='cascade', tracking=True,
        domain="[('product_code_id', '=', product_code_id)]"
    )

    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', default=lambda self: self.env.ref('base.USD'), required=True)

    # ==== Các trường chi phí ====
    material_cost = fields.Float(string="Material.Cost", help="Chi phí nguyên phụ liệu", compute='_compute_total_price',  tracking=True)
    waste_percent = fields.Integer(string="Waste (%)", help="Phần trăm chi phí hao hụt", tracking=True)
    finance_percent = fields.Integer(string="Finance (%)", help="Phần trăm chi phí tài chính", tracking=True)
    waste = fields.Float(string="Waste", compute='_compute_waste_finance',  help="Chi phí hao hụt", tracking=True)
    finance = fields.Float(string="Finance", compute='_compute_waste_finance',  help="Chi phí tài chính", tracking=True)
    total_net = fields.Float(string="Total.Net", help="Tổng chi phí nguyên liệu", compute='_compute_total_net' , tracking=True)
    cut_make = fields.Float(string="CM", help="Tiền công cắt, may, lắp ráp (CM)", tracking=True)
    admin_percent = fields.Integer(string="Admin (%)", help="Phần trăm chi phí quản lý, vận hành (Admin)", tracking=True)
    admin = fields.Float(string="Admin", compute='_compute_admin_cost', help="Chi phí quản lý, vận hành (Admin)", tracking=True)
    inspection_cost = fields.Float(string="Inspection.Cost", help="Chi phí kiểm hàng", tracking=True)
    test_cost = fields.Float(string="Test.Cost", help="Chi phí kiểm nghiệm", tracking=True)
    import_export_cost = fields.Float(string="Import/Export.Cost", help="Chi phí xuất nhập khẩu", tracking=True)
    standard_fob = fields.Float(string="Standard.FOB", help="Giá FOB cơ bản", compute='_compute_standard_fob',  tracking=True)
    surcharge_percent = fields.Integer(string="Surcharge (%)", help="Phần trăm chi phí phụ thu", tracking=True)
    surcharge = fields.Float(string="Surcharge", compute='_compute_surcharge', help="Chi phí phụ thu", tracking=True)
    extra_cost = fields.Float(string="Extra.Cost", help="Chi phí phát sinh khác", tracking=True)
    final_fob = fields.Float(string="Final.FOB", help="Giá FOB cuối cùng", compute='_compute_final_fob', tracking=True)
    agreed_fob = fields.Float(string="Agreed.FOB", help="Giá FOB chốt", tracking=True)

    # ==== Dòng vật tư (tạm thời trong wizard) ====
    line_ids = fields.One2many('product.price.calculation.wizard.line', 'wizard_id', string="Chi tiết vật tư")
    # Hàm đếm số lượng vật tư 
    material_count = fields.Integer(
        string="Material Count",
        compute='_compute_material_count',
        store=False
    )

    @api.depends('line_ids')
    def _compute_material_count(self):
        for record in self:
            record.material_count = len(record.line_ids)
            
    # ==== Thông tin người tạo ====
    date_calculation = fields.Datetime(string='Ngày tính giá', default=fields.Datetime.now, readonly=True)
    employee_id = fields.Many2one(
        'employee.base', 
        string='Người tạo',
        default=lambda self: self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)
        , readonly=True
    )

    # ==== Ràng buộc giá trị phần trăm ====
    @api.constrains('waste_percent', 'finance_percent', 'admin_percent', 'surcharge_percent')
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

    # ==== Các hàm tính toán ====
    @api.depends('line_ids.total_price')
    def _compute_total_price(self):
        for record in self:
            record.material_cost = sum(line.total_price for line in record.line_ids)

    @api.depends('material_cost', 'waste_percent', 'finance_percent')
    def _compute_waste_finance(self):
        for rec in self:
            rec.waste = rec.material_cost * (rec.waste_percent / 100.0)
            rec.finance = rec.material_cost * (rec.finance_percent / 100.0)

    @api.depends('material_cost', 'waste', 'finance')
    def _compute_total_net(self):
        for rec in self:
            rec.total_net = rec.material_cost + rec.waste + rec.finance

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

    @api.depends('standard_fob', 'surcharge_percent')
    def _compute_surcharge(self):
        for rec in self:
            rec.surcharge = rec.standard_fob * (rec.surcharge_percent / 100.0)

    @api.depends('standard_fob', 'surcharge', 'extra_cost')
    def _compute_final_fob(self):
        for rec in self:
            rec.final_fob = rec.standard_fob + rec.surcharge + rec.extra_cost

    # ==== Khi chọn style thì load vật tư ====
    @api.onchange('product_color_size_id')
    def _onchange_style(self):
        """Khi chọn style -> tự động load vật tư từ style."""
        if not self.product_color_size_id:
            self.line_ids = [(5, 0, 0)]
            return

        # 🔹 Nếu đã có dòng (user có thể đang chỉnh sửa) thì không reset
        if self.line_ids:
            return

        materials_in_order = self.product_color_size_id.material_ids
        lines = []
        variant = self.product_color_size_id
        for material in materials_in_order:
            # SỬA LỖI: Lấy định mức theo đúng size VÀ style (color/size) của variant
            correct_norm_line = material.norm_line_ids.filtered(
                lambda norm: norm.size_id.id == variant.size_id.id and norm.color_size_id.id == variant.id
            )
            if not correct_norm_line:
                continue

            consumption = correct_norm_line[0].consumption
            position = correct_norm_line[0].position


            lines.append((0, 0, {
                'program_customer_id': material.id,
                'name': material.mtr_no,
                'position': position,
               # 'mtr_no': material.mtr_no,
              #  'mtr_type': material.mtr_type.id if material.mtr_type else False,
              #  'mtr_code': material.mtr_code,
              #  'mtr_name': material.mtr_name,
              #  'rate': material.rate,
                'dimension': material.dimension,
              #  'color_item': material.color_item,
               # 'color_code': material.color_code,
              #  'color_name': material.color_name,
              #  'color_set': material.color_set,
              #  'supplier': material.supplier.id if material.supplier else False,
                'consumption': consumption,
                'price': material.price,
                'cif_price': material.cif_price,
                'fob_price': material.fob_price,
                'exwork_price': material.exwork_price,
            }))

        self.line_ids = lines
        
    # ==== Khi người dùng nhấn Tạo bảng tính giá ====
    def action_create_calculation(self):
        """Tạo bản ghi product.price.calculation thực sự"""
        self.ensure_one()
        
        # Lấy tất cả các giá trị từ các dòng wizard để tạo bản ghi chính.
        # Logic tạo bản ghi trong model `product.price.calculation` đã đủ thông minh
        # để xử lý dữ liệu này.
        calc = self.env['product.price.calculation'].create({
            'warehouse_order_id': self.warehouse_order_id.id,
            'product_code_id': self.product_code_id.id,
            'product_color_size_id': self.product_color_size_id.id,
            'currency_id': self.currency_id.id,
            
            'waste_percent': self.waste_percent,
            'finance_percent': self.finance_percent,
            'cut_make': self.cut_make,
            'admin_percent': self.admin_percent,
            'inspection_cost': self.inspection_cost,
            'test_cost': self.test_cost,
            'import_export_cost': self.import_export_cost,
            'surcharge_percent': self.surcharge_percent,
            'extra_cost': self.extra_cost,
            'agreed_fob': self.agreed_fob,
            
            # SỬA LỖI: Dùng đúng tên trường là `calculation_line_ids`
            'calculation_line_ids': [
                (0, 0, {
                    'program_customer_id': line.program_customer_id.id,
                    'name': line.name,
                    'position': line.position,
                   # 'mtr_no': line.mtr_no,
                    #'mtr_type': line.mtr_type.id if line.mtr_type else False,
                   # 'mtr_code': line.mtr_code,
                   # 'mtr_name': line.mtr_name,
                   # 'rate': line.rate,
                    'dimension': line.dimension,
                   # 'color_item': line.color_item,
                   # 'color_code': line.color_code,
                   # 'color_name': line.color_name,
                   # 'color_set': line.color_set,
                   # 'supplier': line.supplier.id if line.supplier else False,
                    'consumption': line.consumption,
                    'price': line.price,
                    'cif_price': line.cif_price,
                    'fob_price': line.fob_price,
                    'exwork_price': line.exwork_price,
                }) for line in self.line_ids
            ]
        })
        
        # Trả về action để mở form view của bản ghi vừa tạo
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.price.calculation',
            'view_mode': 'form',
            'res_id': calc.id,
            'target': 'current', # Cải tiến: Mở form mới thay thế cho wizard
        }


# ------------------------------------------------------------------
# Dòng chi tiết vật tư trong wizard
# ------------------------------------------------------------------
class ProductPriceCalculationWizardLine(models.TransientModel):
    _name = 'product.price.calculation.wizard.line'
    _description = 'Dòng vật tư trong Wizard tính giá sản phẩm'

    wizard_id = fields.Many2one('product.price.calculation.wizard', string="Wizard", ondelete='cascade')
    program_customer_id = fields.Many2one('program.customer', string="Vật tư", ondelete='cascade')

    name = fields.Char(string="Mtr#", related='program_customer_id.name', store=True, readonly=True,)  # Mã code vật tư / Mtr No
    mtr_no = fields.Char(string="Mtr_no", related='program_customer_id.mtr_no', )
    
    position = fields.Char( string="Position", help="Vị trí vật tư")
    
    mtr_type = fields.Many2one(related='program_customer_id.mtr_type',string="Mtr Type", help="Loại vật tư",  ) # Loại vật tư /Type
    mtr_name = fields.Char(related='program_customer_id.mtr_name',  string="Mtr Name", help="Tên vật tư")  # Tên vật tư / Mtr Name
    mtr_code = fields.Char(related='program_customer_id.mtr_code', string='Mtr Code', help='Code item của nhà cung cấp')  # Mã nội bộ / Mtr Code
    rate = fields.Char(related='program_customer_id.rate',string="Unit", help='Ví dụ: mét, cuộn, cái...')
    dimension = fields.Char(string="Dimension", related='program_customer_id.dimension', help="Kích thước theo ngữ cảnh")

    material_color_id = fields.Many2one('material.color', related='program_customer_id.material_color_id', string="Màu vật tư",)
    color_item = fields.Char(string="Color#", help="Mã item màu",related='material_color_id.name', ) # Mã màu vật tư / Color# 
    color_code = fields.Char(string="Color Code", help="Mã code màu",related='material_color_id.color_code', ) # Mã code màu / Color Code 
    color_name = fields.Char(string="Color Name", help="Tên màu",related='material_color_id.color_name', ) # Tên màu /Color Name 
    color_set = fields.Char(string="Color Set", help="Bộ màu",related='material_color_id.color_set_id.name',  )
    supplier = fields.Many2one('supplier.partner', string="Supplier", related='program_customer_id.supplier', )
    supplier_index = fields.Char(string="Supplier#", related='supplier.supplier_index', help="Mã số nhà cung cấp")
    country = fields.Char(string="Country", related='program_customer_id.country', )

    consumption = fields.Float(string="Consumption")
    contextual_consumption = fields.Char(string="Định mức áp dụng", help="Định mức theo bối cảnh (nếu có)")
    price = fields.Float(string="Price", digits=(16, 3), related='program_customer_id.price', help="Đơn Giá")
    cif_price = fields.Float(string="CIF.Price", digits=(16, 3), default=0.0, related='program_customer_id.cif_price',  help="Giá CIF")
    fob_price = fields.Float(string="FOB.Price", digits=(16, 3), default=0.0, related='program_customer_id.fob_price',  help="Giá FOB")
    exwork_price = fields.Float(string="EXW.Price", digits=(16, 3), default=0.0, related='program_customer_id.exwork_price', help="Giá EXW")

    total_price = fields.Float(string="Tổng", compute='_compute_total_price', )

    @api.depends('consumption', 'price')
    def _compute_total_price(self):
        for rec in self:
            rec.total_price = rec.consumption * rec.price
