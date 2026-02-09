# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError , AccessError
from datetime import timedelta
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)

class WarehouseOrder(models.Model):
    _name = 'warehouse.order'
    _description = 'Chương trình'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'
    _order = "create_date desc"
#-------------------------------------------------------------    
# region (1) Quy trình 1 tạo chương trình và duyệt chương trình    
    name = fields.Char(string='Tên chương trình', required=True,  tracking=True)
    order_index = fields.Char(string='Mã chương trình', help ="Order Index", 
        copy=False, index=True, readonly=True,default='New') 
    
    # Thông tin chi tiết chương trình     
    customer_id = fields.Many2one('customer.cf', string='Khách hàng', 
        help="Customer", ondelete='cascade',required=True) 
    customer_po_index = fields.Char(string='Mã PO khách hàng', help ="Customer PO Index")
    
    order_date = fields.Datetime(string='Ngày đặt hàng' ,default=fields.Datetime.now, 
                                 redonly=True, tracking=True)
    
    
    expected_date = fields.Datetime(string='Thời gian dự kiến hoàn thành', default=lambda self: self._default_order_date(), tracking=True,)
    @api.model
    def _default_order_date(self):
        """Trả về thời gian mặc định khi tạo mới dựa theo mẫu đề nghị"""
        # Default 2 day if no template
        return datetime.now() + timedelta(days=30) 
    complete_date = fields.Datetime(string='Ngày hoàn thành chương trình', 
                                    redonly=True, tracking=True)  
    pay_term = fields.Char(string='Điều khoản thanh toán', 
                           help="Pay Term")
    ship_term = fields.Char(string='Điều khoản vận chuyển', 
                            help="Ship Term")
    ship_date = fields.Datetime(string='Thời gian giao hàng', 
                                help="Ship Date")
    ship_address = fields.Char(string='Địa chỉ giao hàng', 
                               help="Ship Address")
    ship_way = fields.Char(string='Phương thức vận chuyển', 
                           help="Ship Way")
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.ref('base.USD'),
        required=True,
        help="Currency"
    )
      
    description = fields.Text(string='Mô tả chi tiết về chương trình',required=True,tracking=True)      

    # Tự động gán nhân viên tạo chương trình        
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)  
        return employee.id if employee else False
    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self._get_employee_default(), store=True)
    
    
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")
    price_calculation_ids = fields.One2many('product.price.calculation', 'warehouse_order_id', string="Bảng tính giá sản phẩm")
    
    def action_open_price_calculation(self):
        """
        Trả về một hành động để mở form tạo mới cho product.price.calculation.
        """
        self.ensure_one()
        return {
            'name': 'Bảng tính giá sản phẩm',
            'type': 'ir.actions.act_window',
            'res_model': 'product.price.calculation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_warehouse_order_id': self.id,
            }
        }
        
    attachment_ids = fields.One2many(
        'ir.attachment', 'res_id',
        domain=[('res_model', '=', 'warehouse.order')],
        string="File đính kèm"
    )
    
    # Quy trình phê duyệt 
    allowed_manager_ids = fields.Many2many(
        'employee.base',
        compute='_compute_allowed_approvers',
        string="Allowed Managers"
    )

    allowed_department_approval_ids = fields.Many2many(
        'employee.base',
        compute='_compute_allowed_approvers',
        string="Allowed Department Approvers"
    )

    @api.depends('employee_id')
    def _compute_allowed_approvers(self):
        for record in self:
            if record.employee_id:
                # Lấy người quản lý của người tạo
                managers = record.employee_id.parent_ids
                # Gộp người tạo và người quản lý của họ vào một danh sách duy nhất
                allowed_approvers = record.employee_id | managers
                
                # Gán danh sách người duyệt cho cả hai trường
                record.allowed_manager_ids = [(6, 0, allowed_approvers.ids)]
                record.allowed_department_approval_ids = [(6, 0, allowed_approvers.ids)]
            else:
                record.allowed_manager_ids = False
                record.allowed_department_approval_ids = False

    manager_ids = fields.Many2many(
        'employee.base',
        string="Quản lý phê duyệt",
        relation='warehouse_manager_rel',
        column1='warehouse_id',
        column2='manager_id',
        help="Quản lý phê duyệt",
        required=True,
        domain="[('id', 'in', allowed_manager_ids)]"
    )

    department_approval_id = fields.Many2many(
        'employee.base',
        string="Phê duyệt mức 2",
        relation='warehouse_department_approval_rel',
        column1='warehouse_id',
        column2='department_id',
        help="Phê duyệt mức 2, có thể đồng thời nhiều người duyệt",
        domain="[('id', 'in', allowed_department_approval_ids)]"
    )

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        # Clear selections when employee changes
        self.manager_ids = False
        self.department_approval_id = False
    
    follow_ids = fields.Many2many(
        'employee.base',  
        string="Người theo dõi", 
        relation='warehouse_follow_rel', 
        column1='warehouse_id', 
        column2='user_id',
        help="Người theo dõi" , tracking=True
    )
    
    state_order = fields.Selection([
        ('draft', 'Đang xử lý'),
        ('manager_approval', 'Chờ quản lý duyệt'),
        ('department_approval', 'Chờ phê duyệt mức 2'),
        ('validate', 'Đã duyệt'),
        ('refuse', 'Từ chối'),
        ('cancelled', 'Hủy'),
    ], string='Trạng thái chương trình', default='draft', tracking=True)
    
    material_status = fields.Selection([
        ('ordered', 'Đã đặt đủ hàng'),
        ('received', 'Đã nhập đủ hàng'),
        ('delivered', 'Đã xuất đủ hàng'),
    ], string='Trạng thái vật tư', tracking=True)

    def _check_material_purchase_order_status(self):
        """
        Kiểm tra trạng thái của các đơn đặt hàng vật tư (material.purchase.order).
        Nếu tất cả các PO đều 'enough', cập nhật trạng thái thành 'ordered'.
        """
        for order in self:
            purchase_orders = self.env['material.purchase.order'].search([('order_id', '=', order.id)])
            if purchase_orders and all(po.order_status == 'enough' for po in purchase_orders):
                order.write({'material_status': 'ordered'})
                
    def _check_material_invoice_status(self):
        """
        Kiểm tra trạng thái của các hóa đơn vật tư (material.invoice).
        Nếu tất cả các hóa đơn đều 'stock_in', cập nhật trạng thái thành 'received'.
        """
        for order in self:
            invoices = self.env['material.invoice'].search([('order_id', '=', order.id)])
            if invoices and all(invoice.state == 'stock_in' for invoice in invoices):
                order.write({'material_status': 'received'})
                
    @api.depends('state_order', 'employee_id', 'manager_ids', 'department_approval_id',)
    def _compute_button_visibility(self):
        for record in self:
            user_id = self.env.user.id
            is_admin = self.env.user.has_group('order_management.group_order_management_manager')
            
            # Always show cancel button for admin
            record.show_cancel_button = is_admin or (record.state_order == 'manager_approval' and user_id == record.employee_id.user_id.id)
            
            # Keep other button visibility logic
            record.show_manager_approval_button = record.state_order == 'manager_approval' and user_id in record.manager_ids.mapped('user_id.id')
            record.show_department_approval_button = record.state_order == 'department_approval' and user_id in record.department_approval_id.mapped('user_id.id')
            record.show_refuse_button = (
                (record.state_order == 'manager_approval' and user_id in record.manager_ids.mapped('user_id.id')) or 
                (record.state_order == 'department_approval' and user_id in record.department_approval_id.mapped('user_id.id'))
            )

    show_cancel_button = fields.Boolean(compute="_compute_button_visibility", store=False)
    show_manager_approval_button = fields.Boolean(compute="_compute_button_visibility", store=False)
    show_department_approval_button = fields.Boolean(compute="_compute_button_visibility", store=False)
    show_refuse_button = fields.Boolean(compute="_compute_button_visibility", store=False)  
    
    priority = fields.Selection([
        ('0', ' '),
        ('1', 'Quan trọng'),
        ('2', 'Khẩn cấp')
    ], string='Mức độ ưu tiên', default='0', tracking=True,
       help="Mức độ ưu tiên của đề nghị:\n"
            "- Bình thường: Đề nghị thông thường\n"
            "- Quan trọng: Cần được xử lý sớm\n"
            "- Khẩn cấp: Cần xử lý ngay lập tức") 
    
    state_check = fields.Selection([
        ('Late_Completion', 'Hoàn thành muộn'),
        ('Expired', 'Quá hạn'),
        ('On_Time_Completion', 'Hoàn thành')],
        string='Trạng thái hoàn thành', readonly=True, tracking=True, default= None )
    
    
    next_approver_id = fields.Many2many(
        'employee.base', string="Người phê duyệt tiếp theo",
        compute="_compute_next_approver",
        store=True
    )
    approver_avatar_name_job = fields.Html(
        string="Người phê duyệt",
        compute="_compute_approver_avatar_name_job"
    )
    remaining_time = fields.Char(string='Thời gian còn lại', compute='_compute_remaining_time') 
    
    
    @api.depends('next_approver_id')
    def _compute_approver_avatar_name_job(self):
        for record in self:
            content = ""
            for approver in record.next_approver_id:
                avatar_url = "/web/image/employee.base/%s/image_1920" % approver.id
                content += '''
                        <div class="d-flex">
                            <div class="mr-3" style="display: flex; align-items: center;">
                                <img src="%s" style="width: 35px; height: 35px; border-radius: 50%%; margin-right: 7px;"/>
                            </div>
                            <div style="flex-grow: 1; padding-left: 10px; display: flex; align-items: center;">
                                <div style="flex: 1; text-align: left;">
                                    <span>
                                        <span style="margin-bottom: 2px; font-weight: bold;font-size:14px;">%s</span>
                                        <br/>
                                        <span style="color: gray; font-size:12px;">%s</span>.<span style="color: gray; font-size:12px;">%s</span>
                                    </span>
                                </div>
                            </div>
                        </div>
                ''' % (avatar_url, approver.name, approver.employee_index, approver.job_title)
            record.approver_avatar_name_job = content
            
    @api.depends('state_order', 'manager_ids', 'department_approval_id')
    def _compute_next_approver(self):
        for record in self:
            if record.state_order == 'manager_approval':
                # Người phê duyệt tiếp theo là quản lý
                record.next_approver_id = record.manager_ids
            elif record.state_order == 'department_approval':
                # Người phê duyệt tiếp theo là bộ phận
                record.next_approver_id = record.department_approval_id
            else:
                # Nếu trạng thái không thuộc các mức phê duyệt, để trống
                record.next_approver_id = False
    
    _sql_constraints = [
        ('unique_order_index', 'UNIQUE(order_index)', 'Mã chương trình đã tồn tại!'),
        ('name_uniq', 'unique(name)', 'Tên chương trình đã tồn tại. Vui lòng chọn một tên khác!')]

    @api.constrains('order_index')
    def _check_unique_order_index(self):
        for record in self:
            if record.order_index:
                domain = [
                    ('order_index', '=', record.order_index),
                    ('id', '!=', record.id),
                ]
                if self.search_count(domain) > 0:
                    raise ValidationError('Mã chương trình "%s" đã tồn tại!' % record.order_index)
  
    status_display = fields.Html(
        string="Tiêu đề", 
        compute='_compute_status_display',
        store=True)              
    
    @api.depends('state_check', 'priority', 'name')
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
            
            # Chỉ hiển thị priority khi là Quan trọng hoặc Khẩn cấp
            if record.priority in ['1', '2']:
                priority_colors = {
                    '1': {'bg': '#ffc107', 'text': '#000000'},  # Vàng nền, chữ đen cho quan trọng
                    '2': {'bg': '#dc3545', 'text': '#ffffff'}   # Đỏ nền, chữ trắng cho khẩn cấp
                }
                priority_text = {
                    '1': 'Quan trọng',
                    '2': 'Khẩn cấp'
                }
                
                html_content += f'''
                    <div style="
                        padding: 1px 6px;
                        border-radius: 10px;
                        background-color: {priority_colors[record.priority]['bg']};
                        color: {priority_colors[record.priority]['text']};
                        font-weight: 500;
                        font-size: 10px;
                        display: inline-block;
                    ">
                        {priority_text[record.priority]}
                    </div>
                '''

            # Chỉ hiển thị state_check khi là Expired (Quá hạn)
            if record.state_check == 'Expired':
                html_content += f'''
                    <div style="
                        padding: 1px 6px;
                        border-radius: 10px;
                        background-color: #dc3545;
                        color: white;
                        font-weight: 500;
                        font-size: 10px;
                        display: inline-block;
                    ">
                        Quá hạn
                    </div>
                '''

            html_content += '</div>'  # Đóng div chứa các trạng thái
            html_content += '</div>'  # Đóng div chính
            record.status_display = html_content

    # Quy trình phê duyệt 2 cấp            
    def _get_next_state(self):
        user_id = self.env.user.id
        # Kiểm tra nếu người dùng là quản trị viên
        if self.env.user.has_group('order_management.group_order_management_manager'):
            self.complete_date = fields.Datetime.now()
            return 'validate'
        if self.state_order == 'manager_approval':
            if user_id in self.manager_ids.mapped('user_id.id'):
                if not self.department_approval_id :
                    self.complete_date = fields.Datetime.now()
                    return 'validate'
                if self.department_approval_id:
                    return 'department_approval'
    
        elif self.state_order == 'department_approval':
            if user_id in self.department_approval_id.mapped('user_id.id'):
                self.complete_date = fields.Datetime.now()
                return 'validate'
        return self.state_order

    # Các hành động chuyển trạng thái và phê duyệt khác 
    def action_manager_order(self):
        user_id = self.env.user.id
        if self.state_order != 'manager_approval':
            raise UserError(_('Chỉ có thể phê duyệt các chương trình trong trạng thái "Chờ quản lý duyệt".'))
        if user_id not in self.manager_ids.mapped('user_id.id') and not self.env.user.has_group('order_management.group_order_management_manager'):
            raise UserError(_('Bạn không có quyền phê duyệt chương trình này ở cấp quản lý.'))
        partner_ids = self.follow_ids.mapped('user_id.partner_id.id')
        # Thêm partner của employee_id vào danh sách (nếu có)
        if self.employee_id.user_id and self.employee_id.user_id.partner_id:
            partner_ids.append(self.employee_id.user_id.partner_id.id)       
        # Gửi thông báo phê duyệt
        new_state = self._get_next_state()
        self.write({'state_order': new_state})
            
        activities= self.activity_ids.filtered(lambda a: a.summary == 'Phản hồi từ cấp quản lý')
        activities.action_done()
        self.message_post(
            body=f"quản lý '{self.env.user.name}' đã phê duyệt chương trình'{self.name}'.",
            partner_ids= partner_ids,
            subtype_id=self.env.ref('mail.mt_note').id,
            author_id=self.env.user.partner_id.id if self.env.user.partner_id else False,
            message_type='comment',
        )
        return {
        'type': 'ir.actions.client',
        'tag': 'reload',  # Sử dụng action_reload để reload trang
        }
    
    def action_validate(self):
        user_id = self.env.user.id
        if self.state_order != 'department_approval':
            raise UserError(_('Chỉ có thể phê duyệt các chương trình trong trạng thái "Chờ phê duyệt mức 2".'))
        if user_id not in self.department_approval_id.mapped('user_id.id') and not self.env.user.has_group('order_management.group_order_management_manager'):
            raise UserError(_('Bạn không có quyền phê duyệt chương trình này ở cấp phê duyệt mức 2.'))
        partner_ids = self.follow_ids.mapped('user_id.partner_id.id')
        # Thêm partner của employee_id vào danh sách (nếu có)
        if self.employee_id.user_id and self.employee_id.user_id.partner_id:
            partner_ids.append(self.employee_id.user_id.partner_id.id)           
        self.write({'state_order': 'validate'})

        # Gửi thông báo phê duyệt
        activities= self.activity_ids.filtered(lambda a: a.summary == 'Phản hồi từ cấp phê duyệt mức 2.')
        activities.action_done()
        self.message_post(
            body=f" '{self.env.user.name}' đã phê duyệt chương trình'{self.name}'.",
            partner_ids= partner_ids,
            subtype_id=self.env.ref('mail.mt_note').id,
            author_id=self.env.user.partner_id.id if self.env.user.partner_id else False,
            message_type='comment',
        )
        return {
        'type': 'ir.actions.client',
        'tag': 'reload',  # Sử dụng action_reload để reload trang
        } 

    def action_refuse(self):
        user_id = self.env.user.id
    # Kiểm tra quyền từ chối dựa trên trạng thái hiện tại
        if self.state_order == 'manager_approval' and not self.env.user.has_group('order_management.group_order_management_manager'):
            if user_id not in self.manager_approval_id.mapped('user_id.id'):
                raise UserError(_('Bạn không có quyền từ chối duyệt chương trình này ở cấp quản lý.'))
    
        elif self.state_order == 'department_approval':
            if user_id not in self.department_approval_id.mapped('user_id.id') and not self.env.user.has_group('order_management.group_order_management_manager'):
                raise UserError(_('Bạn không có quyền từ chối duyệt chương trình này ở cấp phê duyệt mức 2.'))

        self.write({'state': 'refuse'})
        self.activity_ids.unlink()
        partner_ids = self.follow_ids.mapped('user_id.partner_id.id')
        # Thêm partner của employee_id vào danh sách (nếu có)
        if self.employee_id.user_id and self.employee_id.user_id.partner_id:
            partner_ids.append(self.employee_id.user_id.partner_id.id)         
        self.message_post(
            body=f"Chương trình '{self.name}' đã bị từ chối bởi '{self.employee_id.name}'.",
            partner_ids= partner_ids,
            subtype_id=self.env.ref('mail.mt_note').id,
            author_id=self.env.user.partner_id.id if self.env.user.partner_id else False,
            message_type='comment',
        )
        return {
        'type': 'ir.actions.client',
        'tag': 'reload',  # Sử dụng action_reload để reload trang
        } 
        
    def action_cancel(self):
        """Cancel order"""
        self.ensure_one()
        self.write({'state_order': 'cancel'})
        
    @api.depends('expected_date', 'complete_date', 'state_order')
    def _compute_remaining_time(self):
        for record in self:
            previous_state_check = record.state_check # Lưu trạng thái trước đó để so sánh
            if record.state_order == 'cancelled':
                # Nếu đề nghị bị hủy, đặt remaining_time và state_check thành trống
                record.remaining_time = ""
                record.state_check = None

            elif record.state_order == 'validate' and record.expected_date and record.complete_date:
                # Trường hợp đề nghị đã hoàn thành hoặc bảo dưỡng hoàn tất
                if record.complete_date > record.expected_date:
                    record.remaining_time = "Hoàn thành muộn"
                    record.state_check = 'Late_Completion'
                else:
                    record.remaining_time = "Hoàn thành"
                    record.state_check = 'On_Time_Completion'

            elif record.order_date:
                # Trường hợp đề nghị chưa hoàn thành, tính thời gian còn lại
                delta = record.expected_date - datetime.now()
                days = delta.days
                hours, remainder = divmod(delta.seconds, 3600)
                minutes, _ = divmod(remainder, 60)

                if delta.total_seconds() >= 0:
                    # Nếu còn thời gian trước khi đến hạn
                    record.remaining_time = f"{days} ngày, {hours} giờ, {minutes} phút"
                    record.state_check = None  # Không quá hạn
                else:
                    # Nếu đã quá hạn
                    record.remaining_time = "Quá hạn"
                    record.state_check = 'Expired'
            else:
                # Nếu không có ngày đến hạn (date_to), để trống remaining_time và state_check
                record.remaining_time = 'N/A'
                record.state_check = None 
            # Gửi thông báo nếu trạng thái chuyển thành 'Expired'
            if previous_state_check != 'Expired' and record.state_check == 'Expired':
                record.message_post(
                    body=f"Chương trình '{record.name}' đã quá hạn vào ngày {record.expected_date.strftime('%d-%m-%Y')} cần được hoàn thành phê duyệt.",
                    partner_ids=record._get_partner_ids(),
                    subtype_id=self.env.ref('mail.mt_note').id,
                    author_id=self.employee_id.user_id.partner_id.id 
                        if self.employee_id.user_id and self.employee_id.user_id.partner_id 
                        else None, 
                ) 
                
    def _get_partner_ids(self):
        """Trả về danh sách `partner_ids` cần thông báo."""
        return list(set(
            ([self.employee_id.user_id.partner_id.id] if self.employee_id.user_id and self.employee_id.user_id.partner_id else []) +
            (self.follow_ids.mapped('user_id.partner_id.id') if self.follow_ids else []) +
            (self.manager_ids.mapped('user_id.partner_id.id') if self.manager_ids else []) +
            (self.department_approval_id.mapped('user_id.partner_id.id') if self.department_approval_id else [])
        )) 
                                 
    @api.model_create_multi
    def create(self, vals_list):
        """
        Ghi đè phương thức create để:
        1. Gán mã theo sequence khi bản ghi được lưu.
        2. Chuyển trạng thái sang 'manager_approval' ngay khi tạo.
        3. Gửi thông báo yêu cầu phê duyệt sau khi tạo.
        """
        for vals in vals_list:
            # 1. Gán mã sequence
            if vals.get('order_index', 'New') == 'New':
                vals['order_index'] = self.env['ir.sequence'].next_by_code('warehouse.order') or 'New'
            # 2. Set initial state
            vals['state_order'] = 'manager_approval'

        # Create the records
        approvals = super(WarehouseOrder, self).create(vals_list)

        # 3. Post-creation logic for each record
        for approval in approvals:
            partner_ids = approval._get_partner_ids()
            approval.message_post(
                body=f"Chương trình '{approval.name}' đã được tạo bởi '{approval.employee_id.name}' và đang chờ duyệt.",
                partner_ids=partner_ids,
                subtype_id=self.env.ref('mail.mt_note').id,
                author_id=approval.employee_id.user_id.partner_id.id
                    if approval.employee_id.user_id and approval.employee_id.user_id.partner_id
                    else None,
            )

        return approvals
    
    @api.model
    def write(self, vals):
        # --- Logic kết hợp: Kiểm tra quyền và gửi thông báo cho 'follow_ids' ---

        # 1. Chuẩn bị cho việc gửi thông báo: Lưu lại danh sách người theo dõi cũ
        #    Phải thực hiện trước khi gọi super() để có trạng thái cũ
        old_followers_map = {}
        if 'follow_ids' in vals:
            old_followers_map = {
                rec.id: rec.follow_ids.mapped('user_id.partner_id')
                for rec in self
            }

            # 2. Kiểm tra quyền: Chỉ thực hiện nếu 'follow_ids' bị thay đổi
            current_user = self.env.user
            is_manager = current_user.has_group('order_management.group_order_management_manager')

            # Nếu người dùng không phải là quản lý, hãy kiểm tra các quyền khác
            if not is_manager:
                for record in self:
                    allowed_users = record.employee_id.user_id | record.manager_ids.mapped('user_id') | record.department_approval_id.mapped('user_id')
                    if current_user not in allowed_users:
                        raise AccessError(_("Bạn không có quyền thay đổi danh sách người theo dõi. Chỉ người tạo, người phê duyệt, hoặc quản lý mới có thể thực hiện hành động này."))

        # 3. Gọi hàm write gốc để lưu thay đổi
        res = super(WarehouseOrder, self).write(vals)

        # 4. Gửi thông báo sau khi đã lưu thành công
        if res and 'follow_ids' in vals:
            for record in self:
                old_partners = old_followers_map.get(record.id, self.env['res.partner'])
                new_partners = record.follow_ids.mapped('user_id.partner_id')
                added_partners = new_partners - old_partners

                if added_partners:
                    record.message_post(
                        body=f"Bạn đã được thêm là người theo dõi cho chương trình '{record.name}'.",
                        partner_ids=added_partners.ids,
                        subtype_id=self.env.ref('mail.mt_note').id,
                        message_type='notification',
                        author_id=record.employee_id.user_id.partner_id.id
                            if record.employee_id.user_id and record.employee_id.user_id.partner_id
                            else self.env.user.partner_id.id,
                    )
        
        return res
    
   # CHẶN WRITE TRÁI QUYỀN
    # ---------------------------

    def action_set_priority_important(self):
        """Set priority to important"""
        self.priority = '1'
        
    def action_set_default_important(self):
        """Set priority to important"""
        self.priority = '0'

    def action_set_priority_urgent(self):
        """Set priority to urgent"""
        self.priority = '2' 
                       
    def action_set_default_urgent(self):
        """Set priority to urgent"""
        self.priority = '0'
            
# endregion

#-------------------------------------------------------------
# region (2) Quy trình tạo Style và vật tư theo chương trình
    product_code_ids = fields.One2many('product.code', 'warehouse_order_id',
        string='Danh sách Style',tracking=True)
    
    all_product_color_size_ids = fields.One2many(
        'product.color.size', 'warehouse_order_id', string='Danh sách style (Màu + Size)'
    )    
    # Tổng hợp danh sách vật tư theo chương trình
    all_material_ids = fields.Many2many(
        'program.customer', 
        'program_customer_warehouse_order_rel', 
        'warehouse_order_id', 
        'program_customer_id', 
        string='Vật tư theo chương trình'
    ) 

    # Danh sách vật tư đặt hàng cho chương trình
    all_material_line = fields.One2many(
        'material.line', 'order_id', string='Danh sách vật tư đặt hàng' )
    

    po_ids = fields.One2many(
        'material.purchase.order',
        'order_id',
        string='Danh sách PO vật tư',tracking=True
    ) 
        
    # Tổng hợp vật tư theo chương trình
    aggregated_material_ids = fields.One2many(
        'warehouse.order.material.line.summary',
        'order_id',
        string='Tổng vật tư theo chương trình',
        compute='_compute_grouped_material_line_ids',
        store=True,
    )
    def action_compute_grouped_materials(self):
        for record in self:
            record._compute_grouped_material_line_ids()
            
    def _compute_grouped_material_line_ids(self):
        # Ensure all dependencies (product.code summaries) are computed first.
        self.mapped('product_code_ids')._compute_grouped_material_line_ids()

        SummaryModel = self.env['warehouse.order.material.line.summary']
        for order in self:
            # Invalidate cache to ensure we read fresh data from the dependencies.
            order.product_code_ids._invalidate_cache(['aggregated_material_ids'])

            # Xóa dòng tổng hợp cũ của chính chương trình này
            SummaryModel.search([('order_id', '=', order.id), ('product_code_id', '=', False)]).unlink()

            group_dict = {}
            # Gộp từ các Style (dữ liệu đã được tính toán và lưu sẵn)
            for product in order.product_code_ids:
                product._compute_grouped_material_line_ids()
                for line in product.aggregated_material_ids:
                    # có cùng vật tư cơ sở, cùng màu vật tư VÀ cùng kích thước.
                    key = (line.program_customer_line_id.id, line.material_color_id.id, line.dimension)
                    if key not in group_dict:
                        group_dict[key] = {
                            'order_id': order.id,
                            'program_customer_line_id': line.program_customer_line_id.id,
                            'material_color_id': line.material_color_id.id,

                            'name': line.name,
                            'mtr_no': line.mtr_no,
                            'mtr_type': line.mtr_type.id if line.mtr_type else False,
                            'mtr_code': line.mtr_code,
                            'mtr_name': line.mtr_name,
                            'rate': line.rate,
                            'dimension': line.dimension,
                            'color_item': line.color_item,
                            'color_code': line.color_code,
                            'color_name': line.color_name,
                            'color_set': line.color_set,
                            'supplier': line.supplier.id if line.supplier else False,
                            'country': line.country,
                            'price': line.price,
                            'cif_price': line.cif_price,
                            'fob_price': line.fob_price,
                            'exwork_price': line.exwork_price,
                            'cons_qty': 0.0,
                        }
                    group_dict[key]['cons_qty'] += line.cons_qty or 0.0

            # Tạo dòng tổng hợp mới cho chương trình (batch create)
            new_summary_lines = self.env['warehouse.order.material.line.summary']
            if group_dict:
                new_summary_lines = SummaryModel.create(list(group_dict.values()))

            # Cập nhật lại giá trị của trường compute
            order.aggregated_material_ids = new_summary_lines
# endregion     
       
#------------------------------------------------------------
# region (3) PHẦN 1: Tìm kiếm, import/export Style           

    product_search_text = fields.Char(string='Tìm kiếm Style')
    product_search_active = fields.Boolean(string='Đang tìm Style', default=False)    

    filtered_product_code_ids = fields.One2many(
        'product.code',
        string='Danh sách Style (đã lọc)',
        compute='_compute_filtered_product_codes',
    )           

    @api.depends('product_code_ids', 'product_search_text')
    def _compute_filtered_product_codes(self):
        for order in self:
            if not order.product_search_text:
                order.filtered_product_code_ids = order.product_code_ids
                continue

            search_text = order.product_search_text.lower()
            filtered_codes = order.product_code_ids.filtered(
                lambda p: search_text in (p.name or '').lower()
            )
            order.filtered_product_code_ids = filtered_codes
            

    @api.onchange('product_search_text')
    def _onchange_product_search_text(self):
        if not self.product_search_text and self.product_search_active:
            self.clear_search_product()

    def button_dummy_product(self):
        return True

    def action_import_product(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Import Style',
            'res_model': 'product.import.export.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
            },
        }
        
    def action_export_product_code(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/export/order_management/{self.id}',
            'target': 'self',
        } 
        
# endregion

# ----------- --------------------------------       
# region (4) PHẦN 2: Tìm kiếm, import/export VẬT TƯ đặt hàng

    # Danh sách vật tư đã được lọc để hiển thị
    filtered_material_line = fields.One2many(
        'material.line',
        string='Danh sách vật tư đặt hàng',
        compute='_compute_filtered_material_line',
        inverse='_inverse_filtered_material_line'
    )

    def _inverse_filtered_material_line(self):
        for order in self:
            # This inverse method now only handles adding new lines.
            # It no longer deletes lines, preventing accidental data loss when filtering.
            # To delete a line, the user must clear filters and delete it from the main list.
            lines_to_add = order.filtered_material_line - order.all_material_line
            if lines_to_add:
                # Set the foreign key on the new lines to link them to the current order
                lines_to_add.write({'order_id': order.id})
                
   # Các trường dùng để tìm kiếm trên giao diện
    material_search_active = fields.Boolean(string='Đang tìm vật tư', default=False)
    material_search_text = fields.Char(string='Tìm kiếm vật tư')
    # Hàm đếm số lượng vật tư 
    material_count = fields.Integer(
        string="Material Count",
        compute='_compute_material_count',
        store=False
    )

    @api.depends('filtered_material_line')
    def _compute_material_count(self):
        for record in self:
            record.material_count = len(record.filtered_material_line)    
            
   # --- Start: Fields for Material Norms Filter ---
    @api.depends('all_material_line')
    def _compute_norm_available_material_types(self):
        for rec in self:
            rec.norm_available_material_type_ids = [(6, 0, rec.all_material_line.mapped('mtr_type').ids)]

    @api.depends('all_material_line')
    def _compute_norm_available_suppliers(self):
        for rec in self:
            rec.norm_available_supplier_ids = [(6, 0, rec.all_material_line.mapped('supplier').ids)]
            
    norm_available_supplier_ids = fields.Many2many('supplier.partner', compute='_compute_norm_available_suppliers')
    norm_available_material_type_ids = fields.Many2many('material.type', compute='_compute_norm_available_material_types')
    search_mtr_type = fields.Many2one('material.type', string="Loại vật tư")
    search_supplier = fields.Many2one('supplier.partner', string="Nhà cung cấp")
   # material_search_active = fields.Boolean(string='Đang tìm vật tư', default=False)
    
    @api.depends('all_material_line', 'material_search_text', 'search_mtr_type', 'search_supplier')
    def _compute_filtered_material_line(self):
        """
        Lọc danh sách vật tư dựa trên các tiêu chí tìm kiếm.
        Kết quả được gán vào trường 'filtered_material_line' và tự động cập nhật trên UI.
        """
        for order in self:
            # Nếu không có tiêu chí tìm kiếm, hiển thị tất cả vật tư
            if not order.material_search_text and not order.search_mtr_type and not order.search_supplier:
                order.filtered_material_line = order.all_material_line
                continue

            # Xây dựng domain (điều kiện) để lọc
            domain = [('id', 'in', order.all_material_line.ids)]
            
            # Thêm điều kiện lọc theo loại vật tư nếu được chọn
            if order.search_mtr_type:
                domain.append(('mtr_type', '=', order.search_mtr_type.id))

            # Thêm điều kiện lọc theo nhà cung cấp nếu được chọn
            if order.search_supplier:
                domain.append(('supplier', '=', order.search_supplier.id))
                
            # Thêm điều kiện lọc theo text (tìm trong các trường mtr_no, mtr_name, mtr_code)
            if order.material_search_text:
                search_text = order.material_search_text
                or_domain = ['|',
                    ('name', 'ilike', search_text),
                    ('mtr_code', 'ilike', search_text),
                ]
                domain.extend(or_domain)
            
            # Thực hiện tìm kiếm và gán kết quả vào trường hiển thị
            order.filtered_material_line = self.env['material.line'].search(domain)
            
    def clear_search_material(self):
        self.ensure_one()
        self.material_search_text = False
        self.search_supplier = False
        self.search_mtr_type = False
        self.material_search_active = False
        self._compute_filtered_material_line()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }


    @api.onchange('material_search_text')
    def _onchange_material_search_text(self):
        '''Xóa tìm kiếm nếu người dùng xóa nội dung nhập'''
        if not self.material_search_text and self.material_search_active:
            self.clear_search_material()

       
    def button_dummy_material(self):
        return True

    def action_import_material(self):
        self.ensure_one()
        return { 
            'type': 'ir.actions.act_window',
            'name': 'Import Vật Tư',
            'res_model': 'material.import.export.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,  # self là warehouse.order
            },
        }
    # export vật tư  trong chương trình theo từng mã hàng
    def action_export_material_warehouse_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/export/warehouse_order/{self.id}',
            'target': 'self',
        }

# endregion

# ----------- --------------------------------       
# region (5) PHẦN 3: Tìm kiếm, import/export VẬT TƯ THEO ĐỊNH MỨC
      
    # Các trường tìm kiếm cho danh sách tổng hợp
    search_agg_mtr_text = fields.Char(string='Tìm trong danh sách tổng hợp')
    search_agg_mtr_active = fields.Boolean(string='Đang tìm vật tư', default=False)
    # Danh sách vật tư tổng hợp ĐÃ LỌC để hiển thị trên giao diện
    filtered_aggregated_material_ids = fields.One2many(
        'warehouse.order.material.line.summary',
        string='Tổng vật tư theo chương trình (đã lọc)',
        compute='_compute_filtered_aggregated_materials',
        store=False,
    )

    @api.depends('aggregated_material_ids', 'search_agg_mtr_text', 'search_mtr_type')
    def _compute_filtered_aggregated_materials(self):
        """
        Lọc danh sách vật tư tổng hợp dựa trên các tiêu chí tìm kiếm.
        """
        for order in self:
            all_aggregated_lines = order.aggregated_material_ids

            # Nếu không có tiêu chí tìm kiếm, hiển thị tất cả
            if not order.search_agg_mtr_text and not order.search_mtr_type:
                order.filtered_aggregated_material_ids = all_aggregated_lines
                continue

            # Lọc dựa trên các tiêu chí
            filtered_lines = all_aggregated_lines

            if order.search_mtr_type:
                filtered_lines = filtered_lines.filtered(
                    lambda l: l.mtr_type == order.search_mtr_type
                )

            if order.search_agg_mtr_text:
                search_text = order.search_agg_mtr_text.lower()
                filtered_lines = filtered_lines.filtered(
                    lambda l: search_text in (l.name or '').lower() or \
                              search_text in (l.mtr_name or '').lower() or \
                              search_text in (l.mtr_code or '').lower() or \
                              search_text in (l.mtr_type.name or '').lower()
                )
            
            order.filtered_aggregated_material_ids = filtered_lines
            
    def action_search_agg_material(self):
        self.ensure_one()
        if not self.search_agg_mtr_text:
            return
        self.search_agg_mtr_active = True
        self._compute_filtered_aggregated_materials()
        return {}

    def clear_search_agg_material(self):
        """Xóa tìm kiếm vật tư tổng hợp"""
        self.ensure_one()
        self.search_agg_mtr_text = False
        self.search_agg_mtr_active = False
        return {}

    @api.onchange('search_agg_mtr_text')
    def _onchange_search_agg_mtr_text(self):
        '''Xóa tìm kiếm nếu người dùng xóa nội dung nhập'''
        if not self.search_agg_mtr_text and self.search_agg_mtr_active:
            self.clear_search_agg_material()
# endregion            
          
# region (6)  PHẦN 4: Tìm kiếm, import/export ĐẶT HÀNG NCC          
    # Tạo các po gửi nhà cung cấp                
    def action_create_po_from_aggregated_materials(self):
        """
        Tạo PO theo từng nhà cung cấp từ danh sách vật tư đã tổng hợp
        """
        # Đảm bảo dữ liệu tổng hợp là mới nhất trước khi tạo PO
        self.action_compute_grouped_materials()

        MaterialLine = self.env['material.line']
        PurchaseOrder = self.env['material.purchase.order']

        for order in self:
            # Check if POs already exist for this order
            existing_pos = PurchaseOrder.search([('order_id', '=', order.id)])
            if existing_pos:
                raise UserError('Các đơn đặt hàng đã được tạo cho chương trình này.')
            
            if not order.aggregated_material_ids:
                raise UserError('Không tìm thấy vật tư nào trong danh sách tổng hợp để tạo PO.')

            grouped_by_supplier = {}

            for line in order.aggregated_material_ids:
                supplier = line.supplier
                if not supplier:
                    continue  # Bỏ qua dòng không có nhà cung cấp

                if supplier not in grouped_by_supplier:
                    grouped_by_supplier[supplier] = []

                grouped_by_supplier[supplier].append(line)

            for supplier, lines in grouped_by_supplier.items():
                po = PurchaseOrder.create({
                    'order_id': order.id,
                    'supplier_id': supplier.id,
                    'name': self.env['ir.sequence'].next_by_code('material.purchase.order') or '/',
                    'date_order': fields.Date.today(),
                })

                for line in lines:
                    MaterialLine.create({
                        'po_id': po.id,
                        
                        'name': line.name,
                        'mtr_no': line.mtr_no,
                        'mtr_type': line.mtr_type.id if line.mtr_type else False,
                        'mtr_code': line.mtr_code,
                        'mtr_name': line.mtr_name,
                        'rate': line.rate,
                        
                        'dimension': line.dimension,
                        
                        'color_item': line.color_item,
                        'color_code': line.color_code,
                        'color_name': line.color_name,
                        'color_set': line.color_set,
                        
                        'supplier': line.supplier.id if line.supplier else False,
                        'country': line.country,
                        'cons_qty': line.cons_qty,
                        
                        'price': line.price,
                        'cif_price': line.cif_price,
                        'fob_price': line.fob_price,
                        'exwork_price': line.exwork_price,
                    })
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
        
    ### Tìm kiếm và lọc danh sách PO vật tư

    filtered_po_ids = fields.One2many(
        'material.purchase.order',
        string='Danh sách PO vật tư (đã lọc)',
        compute='_compute_filtered_po_ids',
        store=False
    )
    @api.depends('po_ids')
    def _compute_po_available_suppliers(self):
        for rec in self:
            rec.po_available_supplier_ids = [(6, 0, rec.po_ids.mapped('supplier_id').ids)]
            
    # Hàm đếm số lượng vật tư 
    supplier_count = fields.Integer(
        string="Supplier Count",
        compute='_compute_supplier_count',
        store=False
    )

    @api.depends('filtered_po_ids')
    def _compute_supplier_count(self):
        for record in self:
            record.supplier_count = len(record.filtered_po_ids)            
            
    po_available_supplier_ids = fields.Many2many('supplier.partner', compute='_compute_po_available_suppliers')
    
    po_search_text = fields.Char(string='Tìm theo tên PO')
    po_search_active = fields.Boolean(string='Đang tìm PO', default=False)
    po_search_supplier = fields.Many2one('supplier.partner', string='Lọc theo nhà cung cấp')
    
    @api.depends('po_ids', 'po_search_text', 'po_search_supplier')
    def _compute_filtered_po_ids(self):  
        for order in self:
            # Nếu không có tiêu chí tìm kiếm, hiển thị tất cả vật tư
            if not order.po_search_text and not order.po_search_supplier:
                order.filtered_po_ids = order.po_ids
                continue

            # Xây dựng domain (điều kiện) để lọc
            domain = [('id', 'in', order.po_ids.ids)]
            
            # Thêm điều kiện lọc theo loại vật tư nếu được chọn
            if order.po_search_supplier:
                domain.append(('supplier_id', '=', order.po_search_supplier.id))
                        # Thêm điều kiện lọc theo nhà cung cấp nếu được chọn

            # Thêm điều kiện lọc theo text (tìm trong các trường mtr_no, mtr_name, mtr_code)
            if order.po_search_text:
                search_text = order.po_search_text
                domain.extend([('name', 'ilike', search_text),])
            
            # Thực hiện tìm kiếm và gán kết quả vào trường hiển thị
            order.filtered_po_ids = self.env['material.purchase.order'].search(domain)
    
    @api.onchange('po_search_text')
    def _onchange_po_search_text(self):
        '''Xóa tìm kiếm nếu người dùng xóa nội dung nhập'''
        if not self.po_search_text and self.po_search_active:
            self.clear_search_po()
    
    # export danh sách đặt hàng NCC
    def action_export_purchase_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/export/order_po/{self.id}',
            'target': 'self',
        }
        
# endregion
    
#-------------------------------------------------------------   
# region (7)  Tạo lệnh sản xuất
    # Tạo lệnh sản xuất
    def action_export_manufacturing_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/export/manufacturing_order/{self.id}',
            'target': 'self',
        }
    # Mở form view Style
    def action_create_product_code(self):
        """Mở form tạo mới Style và truyền sẵn chương trình hiện tại"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tạo mới Style',
            'res_model': 'product.code',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_warehouse_order_id': self.id,
            }
        }
# endregion


