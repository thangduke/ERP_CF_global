from odoo import models, fields, api
import base64
import pandas as pd
import tempfile
import os
import datetime
from odoo.exceptions import ValidationError, UserError

class MaterialInvoice(models.Model):
    _name = 'material.invoice'
    _description = 'Mã Invoice vật tư'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'
    _order = "create_date desc"
    
    name = fields.Char(string="Mã Invoice", required=True, readonly=True, default='New', copy=False, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        """
        Ghi đè phương thức create để gán mã theo sequence khi bản ghi được lưu.
        """
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('material.invoice') or 'New'
        return super(MaterialInvoice, self).create(vals_list)       
    
    def write(self, vals):
        res = super(MaterialInvoice, self).write(vals)
        if 'state' in vals:
            order_ids = self.mapped('order_id')
            if order_ids:
                order_ids._check_material_invoice_status()
        return res
    
    order_id = fields.Many2one('warehouse.order', string="Chương trình",ondelete='cascade' )
    supplier = fields.Many2one('supplier.partner', string="Nhà cung cấp", help="SUPPLIER")
    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.company,)
    
    po_id = fields.Many2one('material.purchase.order', string='Mã đặt hàng NCC', ondelete='set null')
        
    invoice_line_ids = fields.One2many('material.invoice.line', 'invoice_id', string='Danh sách vật tư')
    
    invoice_no = fields.Char(string="INVOICE#", help="Mã Invoice nhà cung cấp")
    # liên kết với model vật tư
    state = fields.Selection([
        ('pending_approval', 'Chờ phê duyệt'),
        ('refused_approval', 'Từ chối phê duyệt'),
        ('draft', 'Đang đặt hàng'),
        ('cancel', 'Đã nhập hàng'),
        ('stock_in', 'Đã nhập kho'),
        ('refuse','Đã hủy đặt hàng'),
    ], string='Trạng thái', default='draft', tracking=True)

    # loại po
    priority = fields.Selection([
        ('1', 'Tạo PO'),
        ('2', 'Đặt thêm PO'),
    ], string='Mức độ ưu tiên', default='1', tracking=True,)
    
    status_display = fields.Html(
        string="Tiêu đề", 
        compute='_compute_status_display',
        store=True)              
    
    @api.depends('state', 'priority', 'name')
    def _compute_status_display(self):
        for record in self:
            html_content = '<div style="display: flex; flex-direction: column; gap: 4px;">'
            
            # Hiển thị tên đề nghị với font size nhỏ hơn và màu mới
            html_content += f'''
                <div style="font-size: 14px; font-weight: 500; color: #335591;  text-align: left;">
                    {record.name or ''}
                </div>
            '''
            
            # Div chứa các trạng thái với kích thước nhỏ hơn
            html_content += '<div style="display: flex; gap: 4px;">'
            
            # Chỉ hiển thị priority khi là '2' (Đặt thêm PO)
            if record.priority == '2':
                priority_color_bg = "#ffc107"  # Đỏ nền
                priority_color_text = '#ffffff' # Chữ trắng
                priority_text = 'Đặt thêm PO'
                
                html_content += f'''
                    <div style="
                        padding: 1px 6px;
                        border-radius: 10px;
                        background-color: {priority_color_bg};
                        color: {priority_color_text};
                        font-weight: 500;
                        font-size: 10px;
                        display: inline-block;
                    ">
                        {priority_text}
                    </div>
                '''


            html_content += '</div>'  # Đóng div chứa các trạng thái
            html_content += '</div>'  # Đóng div chính
            record.status_display = html_content    
                                
    def action_confirm(self):
        self.ensure_one()
        if not self.invoice_no:
            raise UserError("Vui lòng nhập số INVOICE# trước khi xác nhận.")
        self.state = 'cancel'
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    def action_refuse(self):
        self.ensure_one()
        if not self.description:
                raise UserError("Vui lòng nhập mô tả trước khi hủy đặt hàng.")
        self.state = 'refuse'
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)  
        return employee.id if employee else False
    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self._get_employee_default(), store=True)
    
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")
    
    date_create = fields.Datetime(string="Ngày tạo", default=fields.Datetime.now, readonly=True)

    active = fields.Boolean('Active', default=True)
    description = fields.Text('Mô tả',tracking=True)
    description_display = fields.Text('Mô tả', compute='_compute_description_display')

    # Thông tin điều khoản
    terms_conditions = fields.Html(
        string="Terms and Conditions",
    sanitize=False,
    default='''
    <div class="terms">
        <h2>TERMS AND CONDITIONS</h2>
        <div>1. Supplier are required to confirm receipt of P/O immediately</div>
        <div>2. All questions need to be clarified within 2 days after receiving P/O</div>
        <div>3. P/I must be sent to us within 3 days from P/O date with clear mentioned our P/O#, customer, program name ...</div>
        <div>4. Price is understood as: EXWORK</div>
        <div>5. Payment term:</div>
        <div>6. Delivery date:</div>
        <div>7. Allowance:</div>
        <div style="margin-left:15px;">FOR FABRIC: SHORT SHIP OR OVERSHIP 3% IS ACCEPTABLE</div>
        <div style="margin-left:15px;">FOR ACC & ZIP: NO SHORT SHIP OR OVERSHIP IS ACCEPTABLE</div>
        <div>8. Shipment sample: Supplier must send shipment sample 1 week before shipdate (5 units per color or 1 meter of each item)</div>
        <div>9. Shipping details</div>
        <div style="margin-left:15px;">9.1. Consignee: CF GLOBAL THAI BINH JOINT STOCK COMPANY. ADD: DONG LA INDUSTRIAL AREA, DONG LA WARD, DONG HUNG DISTRICT, THAI BINH PROVINCE, VIET NAM. TEL : 84-936680081. FAX :</div>
        <div style="margin-left:15px;">9.2. Collect account:</div>
        <div style="margin-left:15px;">9.3. Ship mode: TBC</div>
        <div style="margin-left:15px;">9.4. Shipping mark:</div>
        <div style="margin-left:30px;">CONSIGNEE: CF GLOBAL THAI BINH JOINT STOCK COMPANY</div>
        <div style="margin-left:30px;">P/O #:</div>
        <div style="margin-left:30px;">P/I #:</div>
        <div style="margin-left:30px;">Carton No:</div>
        <div style="margin-left:30px;">N/W :</div>
        <div style="margin-left:30px;">G/W :</div>
        <div>10. Special note for materials:</div>
        <div style="margin-left:15px;">+ AZO FREE</div>
        <div style="margin-left:15px;">+ NICKEL FREE</div>
        <div style="margin-left:15px;">+ METAL FREE (except for zipper and accessories with KENSIN finish)</div>
        <div>11. Do not pack over 50 kgs (110 lbs)/ package</div>
        <div>12. Material quality needs to follow Customer's standard</div>
        <hr/>
    </div>
    '''
    )

    @api.depends('description')
    def _compute_description_display(self):
        for record in self:
            if record.description:
                record.description_display = record.description
            else:
                record.description_display = 'Không có mô tả'
                
    # Thêm SQL constraint
    _sql_constraints = [
        ('unique_invoice_name', 'UNIQUE(name)', 'Mã Invoice đã tồn tại!')
    ]
    
    # Thêm validate khi tạo/sửa mã
    @api.constrains('name')
    def _check_unique_name(self):
        for record in self:
            if record.name:
                # Kiểm tra xem có record nào khác có cùng tên không
                domain = [
                    ('name', '=', record.name),
                    ('id', '!=', record.id),
                ]
                if self.search_count(domain) > 0:
                    raise ValidationError('Mã Invoice "%s" đã tồn tại!' % record.name)
                                     
                    
    def action_delete_selected_lines(self):
        for rec in self:
            lines_to_delete = rec.line_ids.filtered(lambda l: l.x_selected)
            lines_to_delete.unlink()
            

#-------------------------------------------------------------
# region (1)PHẦN 1: Tìm kiếm, import/export vật tư theo PO ĐẶT HÀNG -----------                  
    filtered_invoice_line_ids = fields.One2many(
        'material.invoice.line',
        'invoice_id',
        string='vật tư theo PO đặt hàng(đã lọc)',
        compute='_compute_filtered_invoice_lines',
        inverse='_inverse_filtered_invoice_lines',
    )
    search_text = fields.Char(string='Search')
    search_active = fields.Boolean(string='Search Active', default=False)
    
    material_count = fields.Integer(
        string="Material Count",
        compute='_compute_material_count',
        store=False
    )

    @api.depends('filtered_invoice_line_ids')
    def _compute_material_count(self):
        for record in self:
            record.material_count = len(record.filtered_invoice_line_ids)  
               
    # --- Start: Fields for Material Norms Filter ---
    @api.depends('invoice_line_ids')
    def _compute_available_material_types(self):
        for rec in self:
            rec.available_material_type_ids = [(6, 0, rec.invoice_line_ids.mapped('mtr_type').ids)]

    available_material_type_ids = fields.Many2many('material.type', compute='_compute_available_material_types')
  
    search_mtr_type = fields.Many2one('material.type', string="Lọc theo Loại vật tư")
    
    @api.depends('invoice_line_ids', 'search_text', 'search_mtr_type')
    def _compute_filtered_invoice_lines(self):
        """
        Lọc danh sách vật tư trên UI dựa trên các tiêu chí tìm kiếm.
        Hàm này hoạt động trên recordset đã có, không query lại database.
        """
        for order in self:
            lines_to_filter = order.invoice_line_ids
            
            # Nếu không có bộ lọc, hiển thị tất cả.
            if not order.search_text and not order.search_mtr_type:
                order.filtered_invoice_line_ids = lines_to_filter
                continue

            # Áp dụng bộ lọc loại vật tư
            if order.search_mtr_type:
                lines_to_filter = lines_to_filter.filtered(
                    lambda line: line.mtr_type and line.mtr_type.id == order.search_mtr_type.id
                )
            
            # Áp dụng bộ lọc text
            if order.search_text:
                search_text = order.search_text.lower()
                lines_to_filter = lines_to_filter.filtered(
                    lambda line: (search_text in (line.name or '').lower()) or \
                                 (search_text in (line.mtr_code or '').lower()) or \
                                 (search_text in (line.mtr_name or '').lower())
                )
            
            order.filtered_invoice_line_ids = lines_to_filter

    def _inverse_filtered_invoice_lines(self):
        """
        Cập nhật an toàn danh sách vật tư chính từ view đã lọc,
        bảo toàn các dòng vật tư đang bị ẩn bởi bộ lọc.
        """
        for invoice in self:
            is_filter_active = invoice.search_text or invoice.search_mtr_type

            # Nếu không có bộ lọc, danh sách hiển thị chính là danh sách đầy đủ.
            if not is_filter_active:
                invoice.invoice_line_ids = invoice.filtered_invoice_line_ids
                continue

            # Nếu có bộ lọc, ta phải hợp nhất các thay đổi.
            
            # 1. Xác định những dòng nào đã được hiển thị cho người dùng.
            # Chạy lại logic lọc để có danh sách chính xác.
            visible_lines = invoice.invoice_line_ids
            if invoice.search_mtr_type:
                visible_lines = visible_lines.filtered(
                    lambda line: line.mtr_type and line.mtr_type.id == invoice.search_mtr_type.id
                )
            if invoice.search_text:
                search_text = invoice.search_text.lower()
                visible_lines = visible_lines.filtered(
                    lambda line: (search_text in (line.name or '').lower()) or \
                                 (search_text in (line.mtr_code or '').lower()) or \
                                 (search_text in (line.mtr_name or '').lower())
                )

            # 2. Xác định những dòng đã bị ẩn.
            hidden_lines = invoice.invoice_line_ids - visible_lines

            # 3. Danh sách đầy đủ mới là hợp của các dòng bị ẩn và các dòng trong view đã lọc.
            invoice.invoice_line_ids = hidden_lines + invoice.filtered_invoice_line_ids

    @api.onchange('search_text')
    def _onchange_search_text(self):
        """Xóa tìm kiếm nếu người dùng xóa nội dung đặt"""
        if not self.search_text and self.search_active:
            self.clear_search()
            
    def button_dummy(self):
        """Empty method for dropdown toggle button"""
        return True
    
    def action_export_material_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'export/material_invoice/{self.id}',
            'target': 'self',
        }


    def action_import(self):
        """Action to import materials for the current invoice"""
        self.ensure_one()  # Đảm bảo chỉ có một bản ghi được chọn

        # Tạo wizard để tải file
        return {
        }  
        
# endregion  
    
    def open_invoice_form_view(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Phiếu đặt hàng',
            'res_model': 'material.invoice',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('order_management.view_material_invoice_form').id,
            'target': 'current',
            'flags': {'mode': 'edit'}
        }
        
    # Tạo action xuất mẫu PDF đặt hàng PO
    def action_report_purchase_order(self):
        self.ensure_one()
        return self.env.ref('order_management.action_report_purchase_order').report_action(self)