from odoo import models, fields, api
from odoo.exceptions import ValidationError

class MaterialDeliveryWizard(models.TransientModel):
    _name = 'material.delivery.wizard'
    _description = 'Wizard to create a material delivery from a receipt'

    date_delivery = fields.Date(string="Ngày xuất", default=fields.Date.today,
            help="Ngày thực hiện xuất kho.")
    
    receive_id = fields.Many2one(
        'material.receive', 
        string="Phiếu nhập kho", 
        required=True,
        domain="[('state', '=', 'done')]"
    )
    
    # Thông tin nơi nhập
    store_id = fields.Many2one('store.list', string="Kho xuất", required=True,
        help="Chọn kho để xuất vật tư.")
    
    order_id = fields.Many2one('warehouse.order', string="Chương trình",
        help="Chương trình sản xuất liên quan đến lần xuất kho này.")
    
    production_name = fields.Char( string="Chuyền sản xuất",
        help="Tên hoặc mã chuyền sản xuất nhận vật tư.")
        
    delivery_line_ids = fields.One2many(
        'delivery.style.wizard.material.line', 
        'wizard_id', 
        string="Danh sách vật tư"
    )
    
    # region(Phần * ) Thông tin người duyệt
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)
        return employee.id if employee else False

    employee_id = fields.Many2one(
        'employee.base', 'Nhân viên xuất',
        default=lambda self: self._get_employee_default(), store=True,
        help="Nhân viên thực hiện thao tác xuất kho."
    )  
    receiver = fields.Many2many ('employee.base', string="Người nhận",
        help="Người hoặc bộ phận nhận vật tư.")
    
    storekeeper_id = fields.Many2one('employee.base', 'Người thủ kho', store=True,
        help="Người thủ kho chịu trách nhiệm quản lý kho vật tư.")
    
    director_id = fields.Many2one('employee.base', 'Giám đốc', store=True,
        help="Giám đốc chịu trách nhiệm phê duyệt.")   
    
    purpose = fields.Char(string="Mục đích xuất kho",
        help="Mục đích cụ thể của việc xuất kho (ví dụ: bán hàng, bảo dưỡng, v.v.).") 
    # endregion  
    
    @api.onchange('receive_id')
    def _onchange_receive_id(self):
        if not self.receive_id:
            self.store_id = False
            self.order_id = False
            self.delivery_line_ids = [(5, 0, 0)]
            return

        self.store_id = self.receive_id.store_id.id
        self.order_id = self.receive_id.order_id.id
        
        delivery_lines = []
        for line in self.receive_id.receive_line_ids:
            delivery_lines.append((0, 0, {
                'material_id': line.material_id.id,
                'qty_received': line.qty,
                'qty': line.qty,
            }))
        
        self.delivery_line_ids = [(5, 0, 0)] + delivery_lines

    def action_create_delivery(self):
        self.ensure_one()
        if not self.delivery_line_ids:
            raise ValidationError("Không có vật tư nào để xuất. Vui lòng tính toán vật tư trước.")

        StockSummary = self.env['material.stock.summary']
        for line in self.delivery_line_ids:
            if line.qty <= 0:
                continue
            
            summary = StockSummary.search([
                ('material_id', '=', line.material_id.id),
                ('store_id', '=', self.store_id.id)
            ], limit=1)
            
            available_qty = summary.qty_closing if summary else 0
            if available_qty < line.qty:
                raise ValidationError(
                    f"Không đủ tồn kho cho vật tư '{line.material_id.display_name}' tại kho '{self.store_id.name}'.\n"
                    f"Số lượng cần: {line.qty}, Tồn kho hiện tại: {available_qty}."
                )

        delivery_vals = {
            'order_id': self.order_id.id,
            'receive_id': self.receive_id.id,
            
            'date_delivery': self.date_delivery,
            'store_id': self.store_id.id,
            
            'production_name': self.production_name,

            'employee_id': self.employee_id.id,
            'receiver': [(6, 0, self.receiver.ids)],
            'storekeeper_id': self.storekeeper_id.id,
            'director_id': self.director_id.id,
            'purpose': self.purpose,
            
            'delivery_line_ids': []
        }
        
        for material_line in self.delivery_line_ids:
            delivery_vals['delivery_line_ids'].append((0, 0, {
                'material_id': material_line.material_id.id,
                'qty': material_line.qty,
            }))

        delivery = self.env['material.delivery'].create(delivery_vals)

        if delivery:
            delivery._create_stock_card_lines()
            delivery._update_stock_summary()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'material.delivery',
            'res_id': delivery.id,
            'view_mode': 'form',
            'target': 'current',
        }
        

class DeliveryStyleWizardMaterialLine(models.TransientModel):
    _name = 'delivery.style.wizard.material.line'
    _description = 'Wizard line for displaying materials from receipt'

    wizard_id = fields.Many2one('material.delivery.wizard', string="Wizard", required=True, ondelete='cascade')
    material_id = fields.Many2one('material.item.line', string="Vật tư", readonly=True)
    
    position = fields.Char( string="Position")
    
    name = fields.Char(related='material_id.name', string="Mtr#")
    
    mtr_no = fields.Char(related='material_id.mtr_no', string='Mtr_no')
    mtr_no_sort_key = fields.Integer(related='material_id.mtr_no_sort_key', string="Sort Key")
    
    mtr_type = fields.Many2one('material.type',string="Mtr_type", related='material_id.mtr_type', )
    mtr_name = fields.Char(related='material_id.mtr_name', string='Mtr_name')
    mtr_code = fields.Char(related='material_id.mtr_code', string='Mtr_Code')
    rate = fields.Char(related='material_id.rate', string="Unit")
    
    dimension = fields.Char(related='material_id.dimension', string='Dimension')
    
    color_item = fields.Char(string="Color#", related='material_id.color_item', help="Mã item màu",)
    color_code = fields.Char(string="Color_code", related='material_id.color_code', help="Mã code màu")
    color_name = fields.Char(string="Color_name", related='material_id.color_name', help="Tên màu")
    color_set = fields.Char(string="Color_set", related='material_id.color_set', help="Bộ màu")

    supplier = fields.Many2one('supplier.partner', string="Supplier", help="Nhà cung cấp vật tư", related='material_id.supplier',)
    country = fields.Char(related='material_id.country', string="Country")

    price = fields.Float(string="Price", related='material_id.price', digits=(16, 3),)
    cif_price = fields.Float(string="CIF.Price", related='material_id.cif_price', digits=(16, 3), help="Giá bán cho khách hàng")
    fob_price = fields.Float(string="FOB.Price", related='material_id.fob_price', digits=(16, 3), help="Giá mua vào")
    exwork_price = fields.Float(string="EXW.Price", related='material_id.exwork_price', digits=(16, 3), help="Giá xuất xưởng")

    qty_received = fields.Float("SL Nhập", readonly=True)
    qty = fields.Float("SL xuất")    
    subtotal = fields.Float("Thành tiền", compute="_compute_subtotal")

    @api.depends("qty", "price")
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.qty * rec.price