from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

class MaterialReceive(models.Model):
    _name = 'material.receive'
    _description = 'Vật tư - Nhập kho'
    _rec_name = 'receipt_no'
    _order = 'create_date desc, id desc'
    
    # Mã nhập kho được liên kết với hàm create
    receipt_no = fields.Char(string="Mã nhập kho", readonly=True, copy=False, help="Mã phiếu nhập kho được tạo tự động.")
    # Đơn hàng liên kết
    order_id = fields.Many2one('warehouse.order', string="Chương trình",  store=True, domain="[('state_order','=','validate')]",
                               help="Chọn chương trình liên quan đến phiếu nhập kho.") 
    # Khách hàng liên kết
    customer_id = fields.Many2one('customer.cf', related='order_id.customer_id', string="Khách hàng", store=True,)
    
    po_id = fields.Many2one('material.purchase.order', string="Mã NCC",  store=True,
        domain="[('order_id', '=', order_id)]",
        help="Chọn Mã nhà cung cấp liên quan đến phiếu nhập kho này.")


    invoice_ids = fields.Many2many('material.invoice', string="Mã PO (Invoice)", required=True,
            help="Chọn PO (Invoice) ở trạng thái 'Đã nhập hàng'.")

    receive_line_ids = fields.One2many('material.receive.line', 'receive_id', string="Chi tiết Nhập kho")       

    # Gán dòng vật tư liên quan
    material_line_ids = fields.One2many('material.invoice.line', 
        compute='_compute_filtered_material_lines',
        string="Xem trước vật tư", store=False)   
        
    # Kho nhập vật tư                   
    store_id = fields.Many2one('store.list', string="Kho", required=True,
                               help="Chọn kho sẽ nhận vật tư.")
    
    supplier = fields.Many2one('supplier.partner',  string="Nhà cung cấp", help="SUPPLIER")
    
    state = fields.Selection([
        ('confirmed', 'Đang xử lý'),
        ('done', 'Hoàn thành'),
        ('cancel', 'Đã hủy'),
    ], string='Trạng thái', default='confirmed', readonly=True, copy=False, tracking=True, help="Trạng thái của phiếu nhập kho.")
    
    @api.onchange('invoice_ids')
    def _onchange_invoice_ids(self):
        """
        - Chỉ kiểm tra điều kiện & cảnh báo
        - KHÔNG tạo receive_line_ids
        - Việc tạo dòng vật tư được xử lý trong create()
        """
        if not self.invoice_ids:
            self.po_id = False
            return

        # 2. Kiểm tra trạng thái hóa đơn
        invalid_invoices = self.invoice_ids.filtered(lambda inv: inv.state != 'cancel')
        if invalid_invoices:
            invoice_names = ', '.join(invalid_invoices.mapped('name'))
            valid_invoices = self.invoice_ids - invalid_invoices
            self.invoice_ids = [(6, 0, valid_invoices.ids)]
            return {
                'warning': {
                    'title': "Lựa chọn không hợp lệ",
                    'message': (
                        f"Các hóa đơn sau không ở trạng thái 'Đã nhập hàng' "
                        f"và đã bị loại bỏ: {invoice_names}."
                    )
                }
            }

        # 3. Kiểm tra cùng PO / NCC
        purchase_orders = self.invoice_ids.mapped('po_id')
        if len(purchase_orders) > 1:
            self.invoice_ids = [(5, 0, 0)]
            return {
                'warning': {
                    'title': "Lỗi lựa chọn",
                    'message': (
                        "Bạn đã chọn các hóa đơn từ nhiều nhà cung cấp khác nhau. "
                        "Vui lòng chỉ chọn các hóa đơn thuộc cùng một nhà cung cấp."
                    ),
                }
            }

        # 4. Kiểm tra hóa đơn đã được dùng ở phiếu khác chưa
        domain = [('invoice_ids', 'in', self.invoice_ids.ids)]
        if self._origin and self._origin.id:
            domain.append(('id', '!=', self._origin.id))

        existed = self.env['material.receive'].search(domain, limit=1)
        if existed:
            self.invoice_ids = [(5, 0, 0)]
            return {
                'warning': {
                    'title': "Cảnh báo trùng lặp",
                    'message': (
                        f"Một hoặc nhiều hóa đơn đã được sử dụng trong "
                        f"phiếu nhập kho '{existed.receipt_no}'."
                    ),
                }
            }

        # 5. Tự động gán PO (chỉ set field, không tạo line)
        self.po_id = purchase_orders[0] if purchase_orders else False


    @api.constrains('invoice_ids')
    def _check_invoice_uniqueness(self):
        """
        Ràng buộc ở mức CSDL để đảm bảo một hóa đơn không thể nằm trong nhiều phiếu nhập kho.
        """
        for rec in self:
            if not rec.invoice_ids:
                continue
            
            domain = [
                ('invoice_ids', 'in', rec.invoice_ids.ids),
                ('id', '!=', rec.id)
            ]
            existed = self.env['material.receive'].search(domain, limit=1)
            
            if existed:
                raise ValidationError(f"Một hoặc nhiều hóa đơn bạn chọn đã được sử dụng trong phiếu nhập kho '{existed.receipt_no}'.")
    
               
    # region (Phần 1: Thông tin nhân sự phiếu nhập )
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)  
        return employee.id if employee else False

    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self._get_employee_default(), store=True,
                                  help="Nhân viên tạo phiếu nhập kho.")
    storekeeper_id = fields.Many2one('employee.base', 'Người thủ kho', store=True,
        help="Người thủ kho chịu trách nhiệm quản lý kho vật tư.")

    deliver_id = fields.Many2one('employee.base', 'Người giao hàng', store=True,
        help="Nhân viên giao hàng vật tư đến kho.")
    
    accountant_id = fields.Many2one('employee.base', 'Kế toán trưởng', store=True,
        help="Nhân viên chịu trách nhiệm quản lý kế toán cho phiếu nhập kho.")
    
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")
    # endregion
    
    date_create = fields.Datetime(string='Ngày tạo', default=fields.Datetime.now, readonly=True)
    
    purpose = fields.Char(string="Mục đích nhập kho" , help="Nhập mô tả ngắn gọn về mục đích của việc nhập kho.")
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # 1. Gán sequence
            if vals.get('receipt_no', 'New') == 'New':
                vals['receipt_no'] = self.env['ir.sequence'].next_by_code(
                    'material.receive'
                ) or 'New'

        # 2. Tạo phiếu nhập kho trước
        records = super(MaterialReceive, self).create(vals_list)

        # 3. Tạo receive_line_ids từ invoice_ids
        for record in records:
            if not record.invoice_ids:
                continue

            merged_lines_data = {}

            for inv_line in record.invoice_ids.mapped('invoice_line_ids'):
                key = (
                    inv_line.mtr_no,
                    inv_line.mtr_type.id,
                    inv_line.dimension,
                    inv_line.color_item,
                    inv_line.supplier.id,
                    inv_line.country,
                )

                if key not in merged_lines_data:
                    merged_lines_data[key] = {
                        'receive_id': record.id,
                        'invoice_line_id': inv_line.id,

                        'name': inv_line.name,
                        'position': inv_line.position,
                        'mtr_no': inv_line.mtr_no,
                        'mtr_no_sort_key': inv_line.name_sort_key,
                        'mtr_type': inv_line.mtr_type.id,
                        'mtr_name': inv_line.mtr_name,
                        'mtr_code': inv_line.mtr_code,
                        'rate': inv_line.rate,

                        'dimension': inv_line.dimension,
                        'color_item': inv_line.color_item,
                        'color_code': inv_line.color_code,
                        'color_name': inv_line.color_name,
                        'color_set': inv_line.color_set,

                        'supplier': inv_line.supplier.id,
                        'country': inv_line.country,

                        'price': inv_line.price,
                        'cif_price': inv_line.cif_price,
                        'fob_price': inv_line.fob_price,
                        'exwork_price': inv_line.exwork_price,

                        'inv_qty': 0.0,
                        'qty': 0.0,

                        'store_id': record.store_id.id,
                    }

                merged_lines_data[key]['inv_qty'] += inv_line.inv_qty
                merged_lines_data[key]['qty'] += inv_line.inv_qty

            # 4. Ghi dòng nhập kho
            receive_lines = [
                (0, 0, vals) for vals in merged_lines_data.values()
            ]

            record.write({
                'receive_line_ids': [(5, 0, 0)] + receive_lines
            })

        return records

    
    def action_done(self):
        """
        Hành động này xử lý logic nhập kho:
        - Cập nhật trạng thái hóa đơn.
        - Tạo/cập nhật vật tư gốc (material.item.line).
        - Cập nhật tồn kho (theo kho và theo chương trình).
        - Ghi thẻ kho.
        """
        item_line_obj = self.env['material.item.line']
        stock_card_obj = self.env['material.stock.card']
        stock_summary_obj = self.env['material.stock.summary']
        program_summary_obj = self.env['material.stock.program.summary']

        for record in self:

            if not record.receive_line_ids:
                raise ValidationError("Không có vật tư nào để nhập kho. Vui lòng thêm vật tư.")

            # Cập nhật trạng thái cho tất cả hóa đơn liên quan
            record.invoice_ids.filtered(lambda inv: inv.state != 'stock_in').write({'state': 'stock_in'})

            # Duyệt qua các dòng nhập kho đã được người dùng xác nhận/chỉnh sửa
            for line in record.receive_line_ids:
                # Bỏ qua nếu số lượng nhập bằng 0
                if line.qty <= 0:
                    continue
                
                # =========================================
                # Step 1: Chuẩn bị dữ liệu và tìm/cập nhật/tạo vật tư gốc
                # =========================================
                item_line_vals = {
                    'name': line.name, 'mtr_no': line.mtr_no, 'position': line.position,
                    'mtr_type': line.mtr_type.id, 'mtr_code': line.mtr_code, 'mtr_name': line.mtr_name,
                    'dimension': line.dimension, 'color_item': line.color_item, 'color_code': line.color_code,
                    'color_name': line.color_name, 'color_set': line.color_set, 'rate': line.rate,
                    'supplier': line.supplier.id, 'price': line.price, 'cif_price': line.cif_price,
                    'fob_price': line.fob_price, 'exwork_price': line.exwork_price,
                }

                # Tìm vật tư gốc dựa trên một khóa duy nhất
                item_line = item_line_obj.search([
                    ('mtr_no', '=', line.mtr_no),
                    ('mtr_code', '=', line.mtr_code),
                    ('supplier', '=', line.supplier.id),
                    ('dimension', '=', line.dimension),
                    ('color_item', '=', line.color_code),
                ], limit=1)

                if item_line:
                    # Nếu tìm thấy, cập nhật nó với thông tin mới nhất từ hóa đơn
                    item_line.write(item_line_vals)
                else:
                    # Nếu không, tạo mới và thêm ngày nhập
                    item_line_vals['entry_date'] = record.date_create
                    item_line = item_line_obj.create(item_line_vals)

                # Liên kết dòng nhập kho với vật tư gốc vừa tạo/cập nhật
                line.write({'material_id': item_line.id})
                
                # =========================================
                # Step 2: Cập nhật tồn theo kho (material.stock.summary)
                # =========================================
                value_add = line.qty * line.price

                # Cập nhật tồn theo kho
                summary = stock_summary_obj.search([
                    ('material_id', '=', item_line.id), ('store_id', '=', record.store_id.id),
                ], limit=1)
                if summary:
                    summary.write({'qty_in': summary.qty_in + line.qty, 'value_in': summary.value_in + value_add})
                else:
                    stock_summary_obj.create({
                        'material_id': item_line.id, 'store_id': record.store_id.id,
                        'qty_in': line.qty, 'value_in': value_add,
                    })

                # =========================================
                # Step 3: Cập nhật tồn theo chương trình (MỚI)
                # =========================================
                program_summary = program_summary_obj.search([
                    ('material_id', '=', item_line.id), ('order_id', '=', record.order_id.id),
                ], limit=1)
                if program_summary:
                    program_summary.write({'qty_in': program_summary.qty_in + line.qty, 'value_in': program_summary.value_in + value_add})
                else:
                    program_summary_obj.create({
                        'material_id': item_line.id, 'order_id': record.order_id.id,
                        'qty_in': line.qty, 'value_in': value_add,
                    })

                # =========================================
                # Step 4: Ghi thẻ kho (stock card)
                # =========================================
                stock_card_obj.create({
                    'material_id': item_line.id, 'order_id': record.order_id.id,
                    'customer_id': record.customer_id.id, 'store_id': record.store_id.id,
                    'movement_type': 'in', 'receive_id': record.id,
                    'qty_in': line.qty, 'value_in': value_add,
                    'date_create': fields.Datetime.now(), 'note': f'Nhập kho {record.receipt_no}',
                })

            # Chuyển trạng thái phiếu sang Hoàn thành
            record.write({'state': 'done'})
        return True

    def action_cancel(self):
        """Chuyển trạng thái phiếu sang Đã hủy."""
        # Cân nhắc thêm logic hoàn trả kho nếu cần trong tương lai
        self.write({'state': 'cancel'})
    
    #region(Phần 2 ) Lọc tìm kiếm vật tư và import , export vật tư 
    # --- Start: Fields for Material Filter ---
    search_text = fields.Char(string='Tìm kiếm vật tư')
    search_mtr_type = fields.Many2one('material.type', string="Lọc theo Loại vật tư")
    available_material_type_ids = fields.Many2many('material.type', compute='_compute_available_options')

    @api.depends('invoice_ids.invoice_line_ids.mtr_type')
    def _compute_available_options(self):
        for rec in self:
            if rec.invoice_ids:
                rec.available_material_type_ids = rec.invoice_ids.mapped('invoice_line_ids.mtr_type')
            else:
                rec.available_material_type_ids = False

    @api.depends('invoice_ids.invoice_line_ids', 'search_text', 'search_mtr_type')
    def _compute_filtered_material_lines(self):
        for rec in self:
            lines_to_filter = rec.invoice_ids.mapped('invoice_line_ids')
            if rec.search_mtr_type:
                lines_to_filter = lines_to_filter.filtered(
                    lambda line: line.mtr_type.id == rec.search_mtr_type.id
                )
            if rec.search_text:
                search_text = rec.search_text.lower()
                lines_to_filter = lines_to_filter.filtered(
                    lambda line: (search_text in (line.name or '').lower()) or \
                                  (search_text in (line.mtr_code or '').lower()) or \
                                  (search_text in (line.mtr_name or '').lower())
                )
            rec.material_line_ids = lines_to_filter   
    
    def action_delete_selected_lines(self):
        # This method seems to operate on `material_line_ids` which are invoice lines.
        # Deleting invoice lines from here might not be intended.
        # If the goal is to delete `receive_line_ids`, this needs to be changed.
        # For now, leaving as is, but flagging for review.
        _logger.warning("action_delete_selected_lines is attempting to delete invoice lines, which may be unintended.")
        for rec in self:
            lines_to_delete = rec.material_line_ids.filtered(lambda l: l.x_selected)
            if lines_to_delete:
                lines_to_delete.unlink()
        
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
        
    def action_report_material_receive(self):
        """Kích hoạt hành động in báo cáo Phiếu Nhập Kho."""
        return self.env.ref('warehouse_pro.action_report_material_receive').report_action(self) 
    
    def action_export_form_receive(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/export/form_receive/{self.id}',
            'target': 'self',
        }     
    #endregion