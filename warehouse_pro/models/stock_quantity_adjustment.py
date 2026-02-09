from odoo import models, fields, api
from odoo.exceptions import ValidationError

class StockQuantityAdjustment(models.Model):
    _name = 'stock.quantity.adjustment'
    _description = 'Yêu cầu điều chỉnh số lượng tồn kho'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string="Mã yêu cầu", copy=False, readonly=True, default='Mới')

    state = fields.Selection([
        ('to_approve', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('rejected', 'Đã từ chối')
    ], string='Trạng thái', default='to_approve', tracking=True)

    # --- Thông tin yêu cầu ---
    @api.model
    def _get_employee_default(self):
        return self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)

    employee_id = fields.Many2one(
        'employee.base',
        string="Người tạo",
        required=True,
        default=_get_employee_default,
        readonly=True
    )
    approver_id = fields.Many2one('employee.base', string="Người duyệt", tracking=True)
    create_date = fields.Date(string="Ngày tạo", default=fields.Date.today, readonly=True)

    # --- Bộ lọc vật tư ---
    warehouse_order_id = fields.Many2one('warehouse.order', string="Chương trình", required=True)
    store_id = fields.Many2one('store.list', string="Kho", required=True)
    shelf_id = fields.Many2one('shelf.list', string="Kệ", domain="[('store_id', '=', store_id)]")
    shelf_level_id = fields.Many2one('shelf.level', string="Khoang", domain="[('shelf_id', '=', shelf_id)]")

    # --- Thông tin điều chỉnh ---
    stock_line_ids = fields.One2many(
        'stock.quantity.adjustment.line',
        'adjustment_id',
        string="Danh sách vật tư điều chỉnh",
    )
    
    display_time = fields.Datetime(string="Thời gian cập nhật", compute='_compute_display_time', readonly=True, store=False)

    @api.depends('write_date', 'create_date')
    def _compute_display_time(self):
        for rec in self:
            rec.display_time = rec.write_date or rec.create_date
            

    reason = fields.Text(string="Lý do điều chỉnh", required=True)

    def _prepare_stock_lines(self):
        """
        Hàm trợ giúp: Chuẩn bị danh sách các giá trị để tạo dòng điều chỉnh
        dựa trên các bộ lọc chương trình và vị trí.
        Nguồn dữ liệu là material.stock.program.summary và material.stock.summary.
        """
        if not self.warehouse_order_id:
            return []

        program_domain = [('warehouse_order_id', '=', self.warehouse_order_id.id)]
        program_summaries = self.env['material.stock.program.summary'].search(program_domain)
        
        material_ids = program_summaries.mapped('material_id').ids
        
        stock_domain = [('material_id', 'in', material_ids)]
        if self.store_id:
            stock_domain.append(('store_id', '=', self.store_id.id))
        if self.shelf_id:
            stock_domain.append(('shelf_id', '=', self.shelf_id.id))
        if self.shelf_level_id:
            stock_domain.append(('shelf_level_id', '=', self.shelf_level_id.id))

        stock_summaries = self.env['material.stock.summary'].search(stock_domain)
        
        program_summary_map = {summary.material_id.id: summary for summary in program_summaries}

        lines_to_create = []
        for stock_summary in stock_summaries:
            program_summary = program_summary_map.get(stock_summary.material_id.id)
            if not program_summary:
                continue

            lines_to_create.append((0, 0, {
                'stock_summary_id': stock_summary.id,
                'program_stock_summary_id': program_summary.id,
                'position': stock_summary.position,
                'name': stock_summary.name,
                'mtr_no': stock_summary.mtr_no,
                'mtr_type': stock_summary.mtr_type.id,
                'mtr_code': stock_summary.mtr_code,
                'mtr_name': stock_summary.mtr_name,
                'dimension': stock_summary.dimension,
                'color_item': stock_summary.color_item,
                'color_name': stock_summary.color_name,
                'color_set': stock_summary.color_set,
                'rate': stock_summary.rate,
                'supplier': stock_summary.supplier.id,
                'country': stock_summary.country,
                'price': stock_summary.price,
                'cif_price': stock_summary.cif_price,
                'fob_price': stock_summary.fob_price,
                'exwork_price': stock_summary.exwork_price,
                'qty_before': stock_summary.qty_closing, 
                'qty_change': stock_summary.qty_closing,
            }))
        return lines_to_create


    @api.onchange('warehouse_order_id', 'store_id', 'shelf_id', 'shelf_level_id')
    def _onchange_filters(self):
        """Tự động tải các dòng vật tư dựa trên bộ lọc."""
        self.stock_line_ids = [(5, 0, 0)]
        if self.warehouse_order_id:
            self.stock_line_ids = self._prepare_stock_lines()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Mới') == 'Mới':
                vals['name'] = f"Điều chỉnh vật tư - {fields.Datetime.now().strftime('%d/%m/%Y %H:%M')}"
        records = super().create(vals_list)

        for rec in records:
            if not rec.stock_line_ids and rec.warehouse_order_id:
                lines = rec._prepare_stock_lines()
                rec.write({'stock_line_ids': lines})

            if not rec.stock_line_ids:
                raise ValidationError("Không tìm thấy vật tư nào khớp với bộ lọc đã chọn.")

            rec.state = "to_approve"
        return records


    def action_approve(self):
        for rec in self:
            if not rec.stock_line_ids:
                raise ValidationError("Không có vật tư nào để điều chỉnh.")

            approver = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)

            for line in rec.stock_line_ids.filtered(lambda l: l.qty_change != l.qty_before):
                if line.qty_change < 0:
                    raise ValidationError("Số lượng mới của vật tư '%s' không được âm." % line.mtr_name)
                
                qty_diff = line.qty_change - line.qty_before
                # Cập nhật số lượng tồn kho trực tiếp vào stock.summary
                if line.stock_summary_id:
                     line.stock_summary_id.qty_closing = line.qty_change # Thay đổi số lượng tồn cuối

                if line.program_stock_summary_id:
                     line.program_stock_summary_id.qty_closing += qty_diff
                # Tạo bản ghi trong stock.card để lưu lại lịch sử điều chỉnh
                '''
                self.env['material.stock.card'].create({
                    'material_id': line.stock_summary_id.material_id.id,
                    'store_id': line.stock_summary_id.store_id.id,
                    'movement_type': 'adjustment',
                    'adjustment_id': rec.id,
                    'qty_out': line.qty_before - line.qty_change if line.qty_before > line.qty_change else 0,
                    'qty_in': line.qty_change - line.qty_before if line.qty_change > line.qty_before else 0,
                    'value_out': (line.qty_before - line.qty_change) * line.price if line.qty_before > line.qty_change else 0,
                    'value_in': (line.qty_change - line.qty_before) * line.price if line.qty_change > line.qty_before else 0,
                    'date_create': fields.Datetime.now(),
                    'note': f"Điều chỉnh tồn kho: {rec.name}. Lý do: {rec.reason or 'Không có'}",
                })'''

            rec.write({'state': 'approved', 'approver_id': approver.id if approver else False})

    def action_reject(self):
        approver = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)
        self.write({'state': 'rejected', 'approver_id': approver.id if approver else False})


    # Tìm kiếm và xóa vật tư đã chọn
    def action_delete_selected_lines(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
           
 #region(Phần 2 ) Chức năng  tìm kiếm và export, import
    # --- Fields for filtering ---
    adj_line_search_text = fields.Char(string='Tìm kiếm vật tư')
    
    adj_line_search_mtr_type = fields.Many2one(
        'material.type',
        string="Lọc theo Loại vật tư",
        domain="[('id', 'in', available_material_type_ids)]"
    )
    adj_line_search_supplier = fields.Many2one(
        'supplier.partner',
        string="Lọc theo Nhà cung cấp",
        domain="[('id', 'in', available_supplier_ids)]"
    )

    # --- Fields for available filter options ---
    @api.depends('stock_line_ids.mtr_type')
    def _compute_available_material_types(self):
        for rec in self:
            if rec.stock_line_ids:
                rec.available_material_type_ids = rec.stock_line_ids.mapped('mtr_type')
            else:
                rec.available_material_type_ids = False

    @api.depends('stock_line_ids.supplier')
    def _compute_available_suppliers(self):
        for rec in self:
            if rec.stock_line_ids:
                rec.available_supplier_ids = rec.stock_line_ids.mapped('supplier')
            else:
                rec.available_supplier_ids = self.env['supplier.partner']

    available_material_type_ids = fields.Many2many('material.type', compute='_compute_available_material_types')
    available_supplier_ids = fields.Many2many('supplier.partner', compute='_compute_available_suppliers')

    # --- Filtered list field ---
    filtered_stock_line_ids = fields.Many2many(
        'stock.quantity.adjustment.line',
        'stock_adj_filtered_line_rel',
        'adjustment_id_m2m',   # Tên cột M2M không được trùng với field name thật!
        'line_id',
        string='Danh sách vật tư (đã lọc)',
        compute='_compute_filtered_stock_lines',
        inverse='_inverse_filtered_stock_lines',
    )

    @api.depends('stock_line_ids', 'adj_line_search_text', 'adj_line_search_mtr_type', 'adj_line_search_supplier')
    def _compute_filtered_stock_lines(self):
        for rec in self:
            lines = rec.stock_line_ids
            is_filter_active = rec.adj_line_search_text or rec.adj_line_search_mtr_type or rec.adj_line_search_supplier
            if not is_filter_active:
                rec.filtered_stock_line_ids = lines
                continue

            if rec.adj_line_search_mtr_type:
                lines = lines.filtered(lambda l: l.mtr_type.id == rec.adj_line_search_mtr_type.id)
            if rec.adj_line_search_supplier:
                lines = lines.filtered(lambda l: l.supplier.id == rec.adj_line_search_supplier.id)
            if rec.adj_line_search_text:
                search_text = rec.adj_line_search_text.lower()
                lines = lines.filtered(
                    lambda l: search_text in (l.mtr_no or '').lower() or \
                            search_text in (l.mtr_code or '').lower() or \
                            search_text in (l.mtr_name or '').lower()
                )
            
            rec.filtered_stock_line_ids = lines

    def _inverse_filtered_stock_lines(self):
        for rec in self:
            # This inverse method handles updates from the filtered view.
            # It combines the changes from the filtered list with the lines that were hidden by the filter.
            
            # Determine which lines were hidden by the filter
            all_lines = rec.stock_line_ids
            
            # Apply the same filter logic to find which lines should be visible
            visible_lines = all_lines
            if rec.adj_line_search_mtr_type:
                visible_lines = visible_lines.filtered(lambda l: l.mtr_type.id == rec.adj_line_search_mtr_type.id)
            if rec.adj_line_search_supplier:
                visible_lines = visible_lines.filtered(lambda l: l.supplier.id == rec.adj_line_search_supplier.id)
            if rec.adj_line_search_text:
                search_text = rec.adj_line_search_text.lower()
                visible_lines = visible_lines.filtered(
                    lambda l: search_text in (l.mtr_no or '').lower() or \
                              search_text in (l.mtr_code or '').lower() or \
                              search_text in (l.mtr_name or '').lower()
                )

            hidden_lines = all_lines - visible_lines
            
            # The new list of stock_line_ids is the union of the (potentially modified) filtered lines
            # and the lines that were hidden.
            rec.stock_line_ids = rec.filtered_stock_line_ids | hidden_lines

    def action_clear_adj_line_filter(self):
        self.ensure_one()
        self.adj_line_search_text = False
        self.adj_line_search_mtr_type = False
        self.adj_line_search_supplier = False
        return {}
 #endregion
    
    
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
        