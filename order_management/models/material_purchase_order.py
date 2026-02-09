from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools import float_compare
from odoo.tools.misc import get_lang

class MaterialPurchaseOrder(models.Model):
    _name = 'material.purchase.order'
    _description = 'Danh sách nhà cung cấp'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'

    display_name = fields.Char(string='Tên hiển thị', compute='_compute_display_name', store=True)
    name = fields.Char(string='Mã NCC', required=True, copy=False, default='New', readonly=True, tracking=True)

    @api.depends('name', 'supplier_id.supplier_index')
    def _compute_display_name(self):
        for order in self:
            if order.supplier_id and order.name:
                order.display_name = f"{order.name} - {order.supplier_id.supplier_index}"
            else:
                order.display_name = order.name or ''

    @api.model_create_multi
    def create(self, vals_list):
        """
        Ghi đè phương thức create để gán mã theo sequence khi bản ghi được lưu.
        """
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('material.purchase.order') or 'New'
        return super(MaterialPurchaseOrder, self).create(vals_list)
        
    def write(self, vals):
        res = super(MaterialPurchaseOrder, self).write(vals)
        if 'order_status' in vals:
            order_ids = self.mapped('order_id')
            if order_ids:
                order_ids._check_material_purchase_order_status()
        return res        
    
    order_id = fields.Many2one('warehouse.order', string='Chương trình', required=True, ondelete='cascade' )
    
    supplier_id = fields.Many2one('supplier.partner', string='Nhà cung cấp', required=True)

    line_ids = fields.One2many('material.line', 'po_id', string='Chi tiết vật tư')

    invoice_ids = fields.One2many('material.invoice', 'po_id', string='po đặt hàng', tracking=True)
    # Xác nhận nhập đủ  
    is_fully_received = fields.Boolean(string='Đã tạo đủ', compute='_compute_is_fully_received', store=True)
    def _compute_is_fully_received(self):
        return
    order_status = fields.Selection(
        [
            ('enough', 'Đặt đủ hàng'),
            ('not_enough', 'Chưa đặt đủ hàng'),
            ('add_po', 'Tạo đặt thêm PO')
        ],
        string='Trạng thái đặt hàng',compute='_compute_order_status',store=True)
    
    manual_add_po = fields.Boolean(string="Tạo thêm PO thủ công", default=False)
    
    @api.depends('line_ids.remaining_qty', 'manual_add_po')
    def _compute_order_status(self):
        for rec in self:
            if rec.manual_add_po:
                rec.order_status = 'add_po'
            elif rec.line_ids and all(line.remaining_qty <= 0 for line in rec.line_ids):
                rec.order_status = 'enough'
            else:
                rec.order_status = 'not_enough'

                
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)  
        return employee.id if employee else False
    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self._get_employee_default(), store=True)
    
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")
    
    date_create = fields.Datetime(string='Ngày tạo', default=fields.Datetime.now, readonly=True)
    
    date_order = fields.Date(string='Ngày tạo đơn', default=fields.Date.today)
    note = fields.Text(string='Ghi chú')   
    description = fields.Text(string='Mô tả', help="Mô tả sản phẩm", tracking=True)
    description_display = fields.Text('Mô tả', compute='_compute_description_display')   
    @api.depends('description')
    def _compute_description_display(self):
        for record in self:
            if record.description:
                record.description_display = record.description
            else:
                record.description_display = 'Không có mô tả'
    
    # Mở wizard tạo PO đặt hàng          
    def action_open_create_invoice_wizard(self):
        self.ensure_one()
        if self.order_status in ['enough', 'add_po']:
            raise UserError("Chương trình này đã đặt đủ hàng. Không thể tạo thêm PO mới.")
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tạo PO đặt hàng theo đợt',
            'res_model': 'material.invoice.create.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_po_id': self.id,
            }
        }
                
    def action_delete_selected_lines(self):
        for rec in self:
            lines_to_delete = rec.material_ids.filtered(lambda l: l.x_selected)
            lines_to_delete.unlink()
          
# region (** )PHẦN *: Duyệt tạo thêm PO đặt hàng  -----------              
    state_approval = fields.Selection([
        ('draft', 'Đang xử lý'),
        ('pending_approval', 'Chờ phê duyệt'),
        ('approved', 'Đã duyệt'),
        ('refused', 'Từ chối'),
        ('cancelled', 'Hủy'),
    ], string='Trạng thái duyệt', default='draft', tracking=True)
    
    allowed_approval_ids = fields.Many2many(
        'employee.base',
        compute='_compute_allowed_approvers',
        string="Allowed Managers"
    )

    @api.depends('employee_id')
    def _compute_allowed_approvers(self):
        for record in self:
            if record.employee_id:
                # Lấy người quản lý của người tạo
                managers = record.employee_id.parent_ids
                # Gộp người tạo và người quản lý của họ vào một danh sách duy nhất
                allowed_approvers = record.employee_id | managers
                record.allowed_approval_ids = [(6, 0, allowed_approvers.ids)]
            else:
                record.allowed_approval_ids = False
                    
    approval_ids = fields.Many2many(
        'employee.base',
        string="Quản lý phê duyệt",
        relation='approval_manager_rel',
        column1='approval_id',
        column2='manager_id',
        required=True,
        domain="[('id', 'in', allowed_approval_ids)]",
        tracking=True
    )   
    
    @api.depends('state_approval', 'employee_id', 'approval_ids',)
    def _compute_button_visibility(self):
        for record in self:
            user_id = self.env.user.id
            is_admin = self.env.user.has_group('order_management.group_order_management_manager')
            # Always show cancel button for admin
            record.show_cancel_button = is_admin or (record.state_approval == 'pending_approval' and user_id == record.employee_id.user_id.id)
            # Keep other button visibility logic
            record.show_manager_approval_button = record.state_approval == 'pending_approval' and user_id in record.approval_ids.mapped('user_id.id')
            record.show_refuse_button = record.state_approval == 'pending_approval' and user_id in record.approval_ids.mapped('user_id.id')

    show_cancel_button = fields.Boolean(compute="_compute_button_visibility", store=False)
    show_manager_approval_button = fields.Boolean(compute="_compute_button_visibility", store=False)
    show_refuse_button = fields.Boolean(compute="_compute_button_visibility", store=False)  
    
    note_approval = fields.Text(string='Ghi chú duyệt')

    # Mở wizard gửi yêu cầu tạo thêm PO
    def action_request_additional_po(self):
        self.ensure_one()
        
        # Kiểm tra xem có yêu cầu nào đang chờ duyệt không
        existing_pending_request = self.env['material.invoice'].search([
            ('po_id', '=', self.id),
            ('priority', '=', '2'),  # Yêu cầu đặt thêm PO
            ('state', '=', 'pending_approval')
        ], limit=1)

        if existing_pending_request:
            raise UserError('Đã có một yêu cầu đặt thêm PO đang chờ phê duyệt. Bạn không thể tạo thêm yêu cầu mới cho đến khi yêu cầu cũ được xử lý.')

        return {
            'type': 'ir.actions.act_window',
            'name': 'Gửi yêu cầu tạo thêm PO',
            'res_model': 'request.add.po.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_po_id': self.id,
            }
        }
    
    def action_confirm(self):
        self.ensure_one()
        self.write({
            'manual_add_po': True,
            'state_approval': 'approved'
        })
        # Tìm và cập nhật trạng thái cho các hóa đơn liên quan
        invoices = self.env['material.invoice'].search([
            ('po_id', '=', self.id),
            ('priority', '=', '2')
        ])
        if invoices:
            invoices.write({'state': 'draft'})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
        
    def action_refuse(self):
        self.ensure_one()
        self.state_approval = 'refuse'
        # Tìm và cập nhật trạng thái cho các hóa đơn liên quan
        invoices = self.env['material.invoice'].search([
            ('po_id', '=', self.id),
            ('priority', '=', '2')
        ])
        if invoices:
            invoices.write({'state': 'refused_approval'})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        } 
        
    def action_cancel(self):
        self.ensure_one()
        self.state_approval = 'cancelled'
        # Tìm và cập nhật trạng thái cho các hóa đơn liên quan
        invoices = self.env['material.invoice'].search([
            ('po_id', '=', self.id),
            ('priority', '=', '2')
        ])
        if invoices:
            invoices.write({'state': 'refuse'})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        } 
         
# endregion  
           
#-------------------------------------------------------------
# region (1) PHẦN 1: Tìm kiếm, import/export danh sách Đặt hàng PO -----------
               
    search_text = fields.Char(string='Search')
    search_active = fields.Boolean(string='Search Active', default=False)

    def action_search(self):
        """Kích hoạt tìm kiếm mà không làm mất dữ liệu gốc"""
        self.ensure_one()
        if not self.search_text:
            return

        self.search_active = True
        return {}

    def clear_search(self):
        """Xóa tìm kiếm và khôi phục danh sách ban đầu"""
        self.ensure_one()
        self.search_text = False
        self.search_active = False

        return {}

    @api.onchange('search_text')
    def _onchange_search_text(self):
        """Xóa tìm kiếm nếu người dùng xóa nội dung nhập"""
        if not self.search_text and self.search_active:
            self.clear_search()
            
    def button_dummy(self):
        """Empty method for dropdown toggle button"""
        return True
    
    def action_export_aggregated_purchase_order(self):
        """Export thông tin khách hàng và định mức liên quan ra file Excel"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/export/purchase_order/{self.id}',
            'target': 'self',
        }
    
    def action_import(self):
        """Action to import materials for the current customer"""
        self.ensure_one()  # Đảm bảo chỉ có một bản ghi được chọn

        # Tạo wizard để tải file
        return { }   
     
# endregion     
  
#-------------------------------------------------------------
# region (2) PHẦN 2: Tìm kiếm, import/export VẬT TƯ ĐẶT HÀNG NCC  -----------

    filtered_material_line = fields.One2many(
        'material.line',
        string='Danh sách vật tư đặt hàng',
        compute='_compute_filtered_material_line',
        inverse='_inverse_filtered_material_line')
    def _inverse_filtered_material_line(self):
        for order in self:
            # Đồng bộ hóa các thay đổi từ danh sách đã lọc trở lại danh sách chính
            # Xóa các dòng đã bị loại bỏ khỏi danh sách lọc
            lines_to_remove = order.line_ids - order.filtered_material_line
            lines_to_remove.unlink()

            # Thêm các dòng mới vào danh sách chính
            lines_to_add = order.filtered_material_line - order.line_ids
            if lines_to_add:
                lines_to_add.write({'po_id': order.id})
                
                
    material_count = fields.Integer(
        string="Material Count",
        compute='_compute_material_count',
        store=False
    )

    @api.depends('filtered_material_line')
    def _compute_material_count(self):
        for record in self:
            record.material_count = len(record.filtered_material_line)    
                       
   # Các trường dùng để tìm kiếm trên giao diện

    material_search_text = fields.Char(string='Tìm kiếm vật tư')
    material_search_active = fields.Boolean(string='Đang tìm vật tư', default=False)
    
    # --- Start: Fields for Material Norms Filter ---
    @api.depends('line_ids')
    def _compute_available_material_types(self):
        for rec in self:
            rec.available_material_type_ids = [(6, 0, rec.line_ids.mapped('mtr_type').ids)]
    available_material_type_ids = fields.Many2many('material.type', compute='_compute_available_material_types')
    
    search_mtr_type = fields.Many2one('material.type', string="Lọc theo Loại vật tư")

    @api.depends('material_search_text', 'search_mtr_type','line_ids')
    def _compute_filtered_material_line(self):
        """
        Lọc danh sách vật tư dựa trên các tiêu chí tìm kiếm.
        Kết quả được gán vào trường 'filtered_material_line' và tự động cập nhật trên UI.
        """
        for order in self:
            # Nếu không có tiêu chí tìm kiếm, hiển thị tất cả vật tư
            if not order.material_search_text and not order.search_mtr_type:
                order.filtered_material_line = order.line_ids
                continue
            # Xây dựng domain (điều kiện) để lọc
            domain = [('id', 'in', order.line_ids.ids)]
            
            # Thêm điều kiện lọc theo loại vật tư nếu được chọn
            if order.search_mtr_type:
                domain.append(('mtr_type', '=', order.search_mtr_type.id))
                 
            # Thêm điều kiện lọc theo text (tìm trong các trường mtr_no, mtr_name, mtr_code)
            if order.material_search_text:
                search_text = order.material_search_text
                domain.extend(['|', '|',
                    ('name', 'ilike', search_text),
                    ('mtr_code', 'ilike', search_text),
                    ('mtr_name', 'ilike', search_text),
                ])
            
            # Thực hiện tìm kiếm và gán kết quả vào trường hiển thị
            order.filtered_material_line = self.env['material.line'].search(domain)
            

    @api.onchange('material_search_text')
    def _onchange_material_search_text(self):
        '''Xóa tìm kiếm nếu người dùng xóa nội dung nhập'''
        if not self.material_search_text and self.material_search_active:
            self.clear_search_material()
             
# endregion  
    
    # MỞ FORM CHI TIẾT ĐẶT HÀNG NCC 
    def open_po_form_view(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'PO vật tư',
            'res_model': 'material.purchase.order',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('order_management.material_purchase_order_form_view').id,
            'target': 'current',
            'flags': {'mode': 'edit'}
        }