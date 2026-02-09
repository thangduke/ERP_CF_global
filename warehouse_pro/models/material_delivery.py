from odoo import models, fields, api
from odoo.exceptions import ValidationError

class MaterialDelivery(models.Model):
    _name = 'material.delivery'
    _description = 'Xuất kho'
    _rec_name = 'delivery_no'
    _order = 'create_date desc, id desc'
    
    delivery_no = fields.Char(string="Số phiếu xuất", copy=False, readonly=True,
        help="Số phiếu xuất kho, được tạo tự động.")   
          
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('confirmed', 'Đang xử lý'),
        ('processing', 'Tạo dòng vật tư'),
        ('done', 'Hoàn thành'),
        ('cancel', 'Đã hủy'),
    ], default='draft')
    
    date_delivery = fields.Date(string="Ngày xuất", default=fields.Date.today,
            help="Ngày thực hiện xuất kho.")
    # Thông tin nơi nhập
    store_id = fields.Many2one('store.list', string="Kho nhập", 
        help="Chọn kho để xuất vật tư.")
    
    # Liên kết hóa đơn nếu có
    order_id = fields.Many2one('warehouse.order', string="Chương trình",required=True,
        help="Chương trình sản xuất liên quan đến lần xuất kho này.")
    
    # --- Totals ---
    total_qty = fields.Float(
        string="Tổng số lượng sản phẩm", 
        compute='_compute_total_qty', 
        store=True,
        help="Tổng số lượng của tất cả các style cần xuất.")

    @api.depends('style_line_ids.quantity')
    def _compute_total_qty(self):
        """Tính tổng số lượng sản phẩm từ các dòng style."""
        for delivery in self:
            delivery.total_qty = sum(line.quantity for line in delivery.style_line_ids)   
            
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
    receiver_id = fields.Char( string="Người nhận",help="Người hoặc bộ phận nhận vật tư.")
    
    storekeeper_id = fields.Many2one('employee.base', 'Người thủ kho', store=True,
        help="Người thủ kho chịu trách nhiệm quản lý kho vật tư.")
    
    director_id = fields.Many2one('employee.base', 'Giám đốc', store=True,
        help="Giám đốc chịu trách nhiệm phê duyệt.")   
    
    purpose = fields.Char(string="Mục đích xuất kho",
        help="Mục đích cụ thể của việc xuất kho (ví dụ: bán hàng, bảo dưỡng, v.v.).")
    
               
    customer_id = fields.Many2one('customer.cf', related='order_id.customer_id', string="Khách hàng",
        help="Khách hàng liên quan (nếu có).")
    
    production_name = fields.Char( string="Chuyền sản xuất",
        help="Tên hoặc mã chuyền sản xuất nhận vật tư.")
    #endregion
    
 # region *Bước 1 Phần Tạo phiếu xuất ** 
    product_code_id = fields.Many2one(
        'product.code', 
        string="Style", 
        required=True,
        domain="[('warehouse_order_id', '=', order_id)]",
        help="Mã sản phẩm (Style) cần dùng vật tư."
    ) 
     
    # Trường mới: Danh sách các Style (Color + Size) cần xuất
    style_line_ids = fields.One2many(
        'material.delivery.style.line', 'delivery_id', 
        string="Danh sách Styles cần xuất",
        help="Chọn các style (màu sắc/kích thước) và nhập số lượng cần xuất cho mỗi loại."
    )   
    '''
    @api.onchange('product_code_id')
    def _onchange_product_code_id_add_styles(self):
        # Clear existing lines first to avoid duplicates when changing the style
        self.style_line_ids = [(5, 0, 0)]
        if self.product_code_id:
            # Find all color/size styles for the selected product code
            styles = self.env['product.color.size'].search([
                ('product_code_id', '=', self.product_code_id.id)
            ])
            
            # Prepare a list of new lines to create
            new_lines = []
            for style in styles:
                new_lines.append((0, 0, {
                    'product_color_size_id': style.id,
                    'quantity': style.total_qty,
                }))
            
            # Assign the new lines to the delivery note
            self.style_line_ids = new_lines
    '''
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('delivery_no', 'New') == 'New':
                vals['delivery_no'] = self.env['ir.sequence'].next_by_code('material.delivery') or 'New'

        records = super(MaterialDelivery, self).create(vals_list)
        return records
    
    def action_confirm_style (self):
        self.ensure_one()
        if not self.style_line_ids:
            raise ValidationError("Vui lòng chọn Style và đảm bảo danh sách Style (màu sắc/kích thước) đã được tạo trước khi xác nhận. Nếu danh sách trống, hãy thử chọn lại Style.")
        self.write({'state': 'confirmed'})
        
    def action_confirm(self):
        self.ensure_one()

        # Lấy tất cả style theo product_code_id
        styles = self.env["product.color.size"].search([
            ("product_code_id", "=", self.product_code_id.id)
        ])

        # Chỉ tạo dòng nếu chưa có (tránh tạo trùng)
        if not self.style_line_ids:
            lines = []
            for style in styles:
                lines.append({
                    "delivery_id": self.id,
                    "product_color_size_id": style.id,
                    "quantity": style.total_qty or 0,
                })
            self.env["material.delivery.style.line"].create(lines)

        return {
            "name": "Chọn Style & Số lượng",
            "type": "ir.actions.act_window",
            "res_model": "material.delivery.style.line",
            "view_mode": "tree,form",
            "target": "current",
            "domain": [("delivery_id", "=", self.id)],
            "context": {
                "default_delivery_id": self.id,
            },
        }
 #endregion

 # region *Bước 2 Phần Tạo Dòng Vật Tư **
    def action_generate_material_lines(self):
        self.ensure_one()
        if not self.style_line_ids:
            raise ValidationError("Chưa có danh sách Style (color-size).")
        # Gọi lại logic tính vật tư
        self._onchange_style_line_ids_recalculate_lines()

        # Chuyển trạng thái
        self.state = "processing"
    
    def _onchange_style_line_ids_recalculate_lines(self):
        """
        Khi danh sách styles hoặc số lượng của chúng thay đổi,
        tự động tính toán lại danh sách và số lượng vật tư cần xuất.
        Tối ưu hóa bằng cách thực hiện một truy vấn duy nhất để tìm tất cả các vật tư.
        """
        # Xóa các dòng cũ trước khi tính toán lại
        self.delivery_line_ids = [(5, 0, 0)]

        if not self.style_line_ids:
            return
        # Trigger computation of aggregated materials for all relevant styles first.
        styles_to_recompute = self.style_line_ids.mapped('product_color_size_id')
        if styles_to_recompute and hasattr(styles_to_recompute, 'action_compute_grouped_materials'):
             styles_to_recompute.action_compute_grouped_materials()
             
        aggregated_materials = {}
        material_search_domains = []

        # Helper để chuẩn hóa các giá trị Char có thể rỗng
        def _normalize_key_part(val):
            if not val or (isinstance(val, str) and not val.strip()):
                return None
            return val

        # 1. Tổng hợp số lượng yêu cầu cho mỗi vật tư duy nhất
        for style_line in self.style_line_ids:
            pcs = style_line.product_color_size_id
            quantity_to_produce = style_line.quantity

            if not pcs or quantity_to_produce <= 0:
                continue

            original_total_qty = pcs.total_qty or 1

            for mat_line in pcs.aggregated_material_ids:
                # Chuẩn hóa các phần của key để đảm bảo so sánh nhất quán
                material_key = (
                    _normalize_key_part(mat_line.mtr_no),
                    mat_line.mtr_type.id,
                    _normalize_key_part(mat_line.mtr_code),
                    mat_line.supplier.id,
                    _normalize_key_part(mat_line.dimension),
                    _normalize_key_part(mat_line.color_item),
                )

                base_rate = mat_line.cons_qty / original_total_qty if original_total_qty != 0 else 0
                required_qty = base_rate * quantity_to_produce

                if material_key in aggregated_materials:
                    aggregated_materials[material_key] += required_qty
                else:
                    aggregated_materials[material_key] = required_qty
                    
                    # Xây dựng domain tìm kiếm linh hoạt cho các trường Char
                    def get_val_domain(field, value):
                        norm_val = _normalize_key_part(value)
                        if norm_val is None:
                            return (field, 'in', [False, '', ' '])
                        return (field, '=', norm_val)

                    domain = [
                        '&', get_val_domain('mtr_no', mat_line.mtr_no),
                        '&', ('mtr_type', '=', mat_line.mtr_type.id),
                        '&', get_val_domain('mtr_code', mat_line.mtr_code),
                        '&', ('supplier', '=', mat_line.supplier.id),
                        '&', get_val_domain('dimension', mat_line.dimension),
                        get_val_domain('color_item', mat_line.color_item)
                    ]
                    material_search_domains.append(domain)

        if not aggregated_materials:
            return

        # 2. Xây dựng một truy vấn lớn để tìm tất cả các vật tư cần thiết
        final_domain = []
        if len(material_search_domains) > 1:
            final_domain = ['|'] * (len(material_search_domains) - 1)
            for domain in material_search_domains:
                final_domain.extend(domain)
        elif material_search_domains:
            final_domain = material_search_domains[0]

        # 3. Thực hiện một truy vấn duy nhất
        found_materials = self.env['material.item.line'].search(final_domain)

        # 4. Tạo map từ key vật tư (đã chuẩn hóa) sang ID vật tư đã tìm thấy
        material_map = {
            (
                _normalize_key_part(m.mtr_no),
                m.mtr_type.id,
                _normalize_key_part(m.mtr_code),
                m.supplier.id,
                _normalize_key_part(m.dimension),
                _normalize_key_part(m.color_item)
            ): m.id
            for m in found_materials
        }

        # 5. Tạo các dòng xuất kho
        delivery_lines_vals = []
        for material_key, qty in aggregated_materials.items():
            material_id = material_map.get(material_key)

            if not material_id:
                name, _, code, *_ = material_key
                raise ValidationError(f"Không tìm thấy vật tư gốc cho vật tư định mức: {name or 'N/A'} ({code or 'N/A'})")

            delivery_lines_vals.append({
                "material_id": material_id,
                "qty": qty,
                "cons_qty": qty,
                "order_id": self.order_id.id,
                "store_id": self.store_id.id,
                "entry_date": self.date_delivery,
            })

        # 6. Cập nhật delivery_line_ids bằng batch create
        self.delivery_line_ids = [(0, 0, vals) for vals in delivery_lines_vals]

    #endregion 
    
 # region *Bước 3 Phần Tạo phiếu xuất hoàn chỉnh **    
    delivery_line_ids = fields.One2many(
        'material.delivery.line', 'delivery_id',
        string="Danh sách vật tư xuất",
    )
    
    def action_done(self):
        self.ensure_one()

        if not self.store_id:
            raise ValidationError("Bạn phải chọn kho xuất trước khi hoàn thành.")
        for line in self.delivery_line_ids:
            # Kiểm tra tồn kho
            stock = self.env['material.stock.summary'].search([
                ('material_id', '=', line.material_id.id),
                ('store_id', '=', self.store_id.id)
            ], limit=1)

            if not stock or stock.qty_closing < line.qty:
                raise ValidationError(
                    f"Vật tư {line.material_id.mtr_no} không đủ tồn kho."
                )

        # Nếu đủ → cập nhật kho
        self._create_stock_card_lines()
        self._update_stock_summary()
        self._update_stock_program_summary()
        self.write({'state': 'done'})
    
    def _create_stock_card_lines(self):
        """Tạo các dòng thẻ kho, có tính toán tồn đầu kỳ."""
        self.ensure_one()
        StockCard = self.env['material.stock.card']
        stock_cards_vals = []

        for line in self.delivery_line_ids:
            if line.qty > 0:
                # Tìm thẻ kho cuối cùng của vật tư này trong kho này
                last_card = StockCard.search([
                    ('material_id', '=', line.material_id.id),
                    ('store_id', '=', self.store_id.id),
                ], order='date_create desc, id desc', limit=1)

                qty_opening = 0
                value_opening = 0
                if last_card:
                    qty_opening = last_card.qty_closing
                    value_opening = last_card.value_closing

                stock_cards_vals.append({
                    'material_id': line.material_id.id,
                    'order_id': self.order_id.id,
                    'customer_id': self.customer_id.id,
                    'store_id': self.store_id.id,
                    'movement_type': 'out',
                    'delivery_id': self.id,
                    'date_create': self.date_delivery, # Sử dụng ngày của phiếu xuất
                    'note': f'Xuất kho theo phiếu {self.delivery_no}',
                    'qty_opening': qty_opening,
                    'value_opening': value_opening,
                    'qty_out': line.qty,
                    'value_out': line.qty * line.price,
                })
        
        if stock_cards_vals:
            StockCard.create(stock_cards_vals)

    def _update_stock_summary(self):
        """Cập nhật tồn kho tổng hợp."""
        self.ensure_one()
        StockSummary = self.env['material.stock.summary']
        for line in self.delivery_line_ids:
            if line.qty > 0:
                summary = StockSummary.search([
                    ('material_id', '=', line.material_id.id),
                    ('store_id', '=', self.store_id.id)
                ], limit=1)
                
                value_out = line.qty * line.price
                
                if summary:
                    # Nếu tìm thấy, cập nhật số lượng và giá trị xuất
                    summary.write({
                        'qty_out': summary.qty_out + line.qty,
                        'value_out': summary.value_out + value_out
                    })
                else:
                    # Nếu không tìm thấy, tạo mới bản ghi tổng hợp.
                    # Điều này xử lý trường hợp xuất kho lần đầu hoặc khi tồn kho có thể âm.
                    StockSummary.create({
                        'material_id': line.material_id.id,
                        'store_id': self.store_id.id,
                        'qty_out': line.qty,
                        'value_out': value_out,
                    })
        
    def _update_stock_program_summary(self):
        """Cập nhật tồn kho tổng hợp theo chương trình."""
        self.ensure_one()
        ProgramSummary = self.env['material.stock.program.summary']
        for line in self.delivery_line_ids:
            if line.qty > 0:
                # Tìm kiếm bản ghi tổng hợp dựa trên vật tư và chương trình
                summary = ProgramSummary.search([
                    ('material_id', '=', line.material_id.id),
                    ('order_id', '=', self.order_id.id)
                ], limit=1)
                
                value_out = line.qty * line.price
                
                if summary:
                    # Nếu tìm thấy, cập nhật số lượng và giá trị xuất
                    summary.write({
                        'qty_out': summary.qty_out + line.qty,
                        'value_out': summary.value_out + value_out,
                    })
                else:
                    # Nếu không tìm thấy, tạo mới bản ghi tổng hợp
                    ProgramSummary.create({
                        'material_id': line.material_id.id,
                        'order_id': self.order_id.id,
                        'qty_out': line.qty,
                        'value_out': value_out,
                    })
 #endregion
    def action_cancel(self):
        self.write({'state': 'cancel'})

    

    #region(Phần 2 ) Chức năng  tìm kiếm và export, import
    def action_delete_selected_lines(self):
        for rec in self:
            lines_to_delete = rec.material_line_ids.filtered(lambda l: l.x_selected)
            lines_to_delete.unlink()
            
    # --- Fields for filtering ---
    delivery_line_search_text = fields.Char(string='Tìm kiếm vật tư')
    
    delivery_line_search_mtr_type = fields.Many2one(
        'material.type',
        string="Lọc theo Loại vật tư",
        domain="[('id', 'in', available_material_type_ids)]"
    )
    delivery_line_search_supplier = fields.Many2one(
        'supplier.partner',
        string="Lọc theo Nhà cung cấp",
        domain="[('id', 'in', available_supplier_ids)]"
    )

    # --- Fields for available filter options ---
    @api.depends('delivery_line_ids.material_id.mtr_type')
    def _compute_available_material_types(self):
        for rec in self:
            if rec.delivery_line_ids:
                rec.available_material_type_ids = rec.delivery_line_ids.mapped('material_id.mtr_type')
            else:
                rec.available_material_type_ids = False

    @api.depends('delivery_line_ids.material_id.supplier')
    def _compute_available_suppliers(self):
        for rec in self:
            if rec.delivery_line_ids:
                rec.available_supplier_ids = rec.delivery_line_ids.mapped('material_id.supplier')
            else:
                rec.available_supplier_ids = False

    available_material_type_ids = fields.Many2many('material.type', compute='_compute_available_material_types')
    available_supplier_ids = fields.Many2many('supplier.partner', compute='_compute_available_suppliers')

    # --- Filtered list field ---
    filtered_delivery_line_ids = fields.Many2many(
        'material.delivery.line',
        'material_delivery_filtered_line_rel',
        'delivery_id',
        'line_id',
        string='Danh sách vật tư (đã lọc)',
        compute='_compute_filtered_delivery_lines',
        inverse='_inverse_filtered_delivery_lines',
    )

    @api.depends('delivery_line_search_text', 'delivery_line_search_mtr_type', 'delivery_line_search_supplier', 'delivery_line_ids')
    def _compute_filtered_delivery_lines(self):
        for rec in self:
            is_filter_active = rec.delivery_line_search_text or rec.delivery_line_search_mtr_type or rec.delivery_line_search_supplier
            if not is_filter_active:
                rec.filtered_delivery_line_ids = rec.delivery_line_ids
                continue

            domain = [('id', 'in', rec.delivery_line_ids.ids)]
            if rec.delivery_line_search_mtr_type:
                domain.append(('material_id.mtr_type', '=', rec.delivery_line_search_mtr_type.id))
            if rec.delivery_line_search_supplier:
                domain.append(('material_id.supplier', '=', rec.delivery_line_search_supplier.id))
            if rec.delivery_line_search_text:
                search_text = rec.delivery_line_search_text
                domain.extend(['|',
                    ('material_id.mtr_no', 'ilike', search_text),
                    ('material_id.mtr_code', 'ilike', search_text),
                ])
            
            rec.filtered_delivery_line_ids = self.env['material.delivery.line'].search(domain)

    def _inverse_filtered_delivery_lines(self):
        for rec in self:
            is_filter_active = rec.delivery_line_search_text or rec.delivery_line_search_mtr_type or rec.delivery_line_search_supplier

            if not is_filter_active:
                rec.delivery_line_ids = rec.filtered_delivery_line_ids
                continue

            original_ids = set(rec.delivery_line_ids.ids)

            domain = [('id', 'in', list(original_ids))]
            if rec.delivery_line_search_mtr_type:
                domain.append(('material_id.mtr_type', '=', rec.delivery_line_search_mtr_type.id))
            if rec.delivery_line_search_supplier:
                domain.append(('material_id.supplier', '=', rec.delivery_line_search_supplier.id))
            if rec.delivery_line_search_text:
                search_text = rec.delivery_line_search_text
                domain.extend(['|',
                    ('material_id.mtr_no', 'ilike', search_text),
                    ('material_id.mtr_code', 'ilike', search_text),
                ])
            
            shown_item_ids = set(self.env['material.delivery.line'].search(domain).ids)
            hidden_item_ids = original_ids - shown_item_ids
            kept_filtered_item_ids = set(rec.filtered_delivery_line_ids.ids)
            new_delivery_line_ids = list(hidden_item_ids | kept_filtered_item_ids)
            
            rec.delivery_line_ids = [(6, 0, new_delivery_line_ids)]

    def action_clear_delivery_line_filter(self):
        self.ensure_one()
        self.delivery_line_search_text = False
        self.delivery_line_search_mtr_type = False
        self.delivery_line_search_supplier = False
        return {}
            
    def button_dummy(self):
        """Empty method for dropdown toggle button"""
        return True
    
    def action_export(self):
        """Export danh sách vật tư trong đơn nhập kho"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/export/material_receive/{self.id}',
            'target': 'self',
        }
    #endregion
        
    def action_report_material_delivery(self):
        """Kích hoạt hành động in báo cáo Phiếu Xuất Kho."""
        return self.env.ref('warehouse_pro.action_report_material_delivery').report_action(self)
    
    # Xuất file Excel Phiếu Xuất Kho
    def action_export_form_delivery(self):
        """Xuất file Excel Phiếu Xuất Kho"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/export/form_delivery/{self.id}',
            'target': 'self',
        }
    # action chon style(Size + So luong)
    def action_open_style_selector(self):
        self.ensure_one()
       
    #endregion
    
    
class MaterialDeliveryStyleLine(models.Model):
    """
    Model này đại diện cho một dòng trong phiếu xuất kho,
    liên kết một 'Style (Color + Size)' cụ thể với số lượng cần xuất.
    """
    _name = 'material.delivery.style.line'
    _description = 'Dòng Style cho Phiếu Xuất Kho'

    delivery_id = fields.Many2one('material.delivery', string="Phiếu Xuất Kho", ondelete='cascade')

    product_code_id = fields.Many2one(related='delivery_id.product_code_id', store=True)
    
    product_color_size_id = fields.Many2one(
        'product.color.size',
        string="Style (Color + Size)",
        domain="[('product_code_id', '=', product_code_id)]",
        help="Chọn phiên bản màu sắc và kích thước của sản phẩm."
    )
    quantity = fields.Integer(
        string="Số lượng cần xuất", 
        default=1.0, 
        help="Số lượng sản phẩm cần sản xuất cho style này."
    )
    @api.onchange('product_color_size_id')
    def _onchange_product_color_size_id(self):
        if self.product_color_size_id:
            self.quantity = self.product_color_size_id.total_qty