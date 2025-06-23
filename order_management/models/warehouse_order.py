# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)

class WarehouseOrder(models.Model):
    _name = 'warehouse.order'
    _description = 'Đơn hàng'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'
    _order = "create_date desc"
#-------------------------------------------------------------    
# region (1) Quy trình 1 tạo đơn hàng và duyệt đơn hàng     
    name = fields.Char(string='Tên Đơn hàng')
    order_index = fields.Char(string='Mã đơn hàng', copy=False, index=True)
    customer_id = fields.Many2one('customer.cf', string='Khách hàng', ondelete='cascade')      
    # Tự động gán nhân viên tạo đơn hàng        
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)  
        return employee.id if employee else False
    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self._get_employee_default(), store=True)
    
    
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")
    attachment_ids = fields.One2many(
        'ir.attachment', 'res_id',
        domain=[('res_model', '=', 'warehouse.order')],
        string="File đính kèm"
    )
    
    manager_ids = fields.Many2many(
        'employee.base', 
        string="Quản lý phê duyệt", 
        relation='warehouse_manager_rel', 
        column1='warehouse_id', 
        column2='manager_id',
        help="quản lý phê duyệt"
    )
    
    department_approval_id = fields.Many2many(
        'employee.base',  
        string="Phòng ban phê duyệt", 
        relation='warehouse_department_approval_rel', 
        column1='warehouse_id', 
        column2='department_id',
        help="Phê duyệt"
    )
    
    follow_ids = fields.Many2many(
        'employee.base',  
        string="Người theo dõi", 
        relation='warehouse_follow_rel', 
        column1='warehouse_id', 
        column2='user_id',
        help="Người theo dõi"
    )
    
    state_order = fields.Selection([
        ('draft', 'Đang xử lý'),
        ('manager_approval', 'Chờ quản lý duyệt'),
        ('department_approval', 'Chờ phòng ban duyệt'),
        ('validate', 'Đã duyệt'),
        ('refuse', 'Từ chối'),
        ('cancelled', 'Hủy'),
    ], string='Trạng thái đơn hàng', default='draft', tracking=True)

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
    
    order_date = fields.Datetime(string='Ngày đặt hàng' ,default=fields.Datetime.now, redonly=True, tracking=True)
    expected_date = fields.Datetime(string='Thời gian dự kiến hoàn thành', default=lambda self: self._default_order_date(), tracking=True,)
    complete_date = fields.Datetime(string='Ngày hoàn thành đơn hàng', redonly=True, tracking=True)
    @api.model
    def _default_order_date(self):
        """Trả về thời gian mặc định khi tạo mới dựa theo mẫu đề nghị"""
        # Default 2 day if no template
        return datetime.now() + timedelta(days=2) 
    
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
    
    description = fields.Text(string='Mô tả chi tiết về đơn hàng')
    
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
                # Người phê duyệt tiếp theo là phòng ban
                record.next_approver_id = record.department_approval_id
            else:
                # Nếu trạng thái không thuộc các mức phê duyệt, để trống
                record.next_approver_id = False
            

    
    _sql_constraints = [
        ('unique_order_index', 'UNIQUE(order_index)', 'Mã đơn hàng đã tồn tại!')]

    @api.constrains('order_index')
    def _check_unique_order_index(self):
        for record in self:
            if record.order_index:
                domain = [
                    ('order_index', '=', record.order_index),
                    ('id', '!=', record.id),
                ]
                if self.search_count(domain) > 0:
                    raise ValidationError('Mã đơn hàng "%s" đã tồn tại!' % record.order_index)
  
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
            raise UserError(_('Chỉ có thể phê duyệt các yêu cầu trong trạng thái "Chờ quản lý duyệt".'))
        if user_id not in self.manager_ids.mapped('user_id.id') and not self.env.user.has_group('order_management.group_order_management_manager'):
            raise UserError(_('Bạn không có quyền phê duyệt yêu cầu này ở cấp quản lý.'))
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
            body=f"quản lý '{self.env.user.name}' đã phê duyệt đề nghị'{self.name}'.",
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
            raise UserError(_('Chỉ có thể phê duyệt các yêu cầu trong trạng thái "Chờ phòng ban duyệt".'))
        if user_id not in self.department_approval_id.mapped('user_id.id') and not self.env.user.has_group('order_management.group_order_management_manager'):
            raise UserError(_('Bạn không có quyền phê duyệt yêu cầu này ở cấp phòng ban.'))
        partner_ids = self.follow_ids.mapped('user_id.partner_id.id')
        # Thêm partner của employee_id vào danh sách (nếu có)
        if self.employee_id.user_id and self.employee_id.user_id.partner_id:
            partner_ids.append(self.employee_id.user_id.partner_id.id)           
        self.write({'state_order': 'validate'})

        # Gửi thông báo phê duyệt
        activities= self.activity_ids.filtered(lambda a: a.summary == 'Phản hồi từ cấp Tổng GĐ')
        activities.action_done()
        self.message_post(
            body=f"Tổng GĐ '{self.env.user.name}' đã phê duyệt đề nghị'{self.name}'.",
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
                raise UserError(_('Bạn không có quyền từ chối yêu cầu này ở cấp quản lý.'))
    
        elif self.state_order == 'department_approval':
            if user_id not in self.department_approval_id.mapped('user_id.id') and not self.env.user.has_group('order_management.group_order_management_manager'):
                raise UserError(_('Bạn không có quyền từ chối yêu cầu này ở cấp quản lý.'))

        self.write({'state': 'refuse'})
        self.activity_ids.unlink()
        partner_ids = self.follower_id.mapped('user_id.partner_id.id')
        # Thêm partner của employee_id vào danh sách (nếu có)
        if self.employee_id.user_id and self.employee_id.user_id.partner_id:
            partner_ids.append(self.employee_id.user_id.partner_id.id)         
        self.message_post(
            body=f"Đề nghị '{self.name}' đã bị từ chối bởi '{self.employee_id.name }'.",
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
                    body=f"Đề nghị phê duyệt '{record.name}' đã quá hạn vào ngày {record.expected_date.strftime('%d-%m-%Y')}.",
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
                                 
    @api.model
    def create(self, vals):
            
        approval = super(WarehouseOrder, self).create(vals)
        approval.state_order = 'manager_approval'
        partner_ids = approval._get_partner_ids()
        #   Loại bỏ các giá trị trùng lặp
        approval.message_post(
            body=f"Đề nghị phê duyệt '{approval.name}' đã được tạo bởi '{approval.employee_id.name}' và đang chờ duyệt.",
            partner_ids= partner_ids, 
            subtype_id=self.env.ref('mail.mt_note').id,
            author_id=approval.employee_id.user_id.partner_id.id 
                if approval.employee_id.user_id and approval.employee_id.user_id.partner_id 
                else None,)
        return approval 
            
# endregion

#-------------------------------------------------------------
# region (2) Quy trình tạo mã hàng và vật tư theo đơn hàng 

    product_code_ids = fields.One2many('product.code', 'warehouse_order_id',
        string='Danh sách mã hàng')
    
    # Tổng hợp danh sách vật tư theo đơn hàng
    all_material_ids = fields.One2many(
        'program.customer', 'warehouse_material_id', string='Định mức khách hàng'
    ) 
    all_product_color_size_ids = fields.One2many(
        'product.color.size', 'warehouse_order_id', string='Danh sách biến thể (Màu + Size)'
    )    
    po_ids = fields.One2many(
        'material.purchase.order',
        'order_id',
        string='Danh sách PO vật tư'
    )
    aggregated_material_ids = fields.One2many(
        'warehouse.order.material.line.summary',
        'order_id',
        string='Tổng vật tư theo đơn hàng',
        compute='_compute_grouped_material_line_ids',
        store=False,
    )
    def action_compute_grouped_materials(self):
        for record in self:
            record._compute_grouped_material_line_ids()
            
    def _compute_grouped_material_line_ids(self):
        SummaryModel = self.env['warehouse.order.material.line.summary']
        for order in self:
            # Xoá dữ liệu cũ
            SummaryModel.search([('order_id', '=', order.id)]).unlink()

            group_dict = {}

            # Tính tổng từ tất cả mã hàng thuộc đơn hàng
            for code in order.product_code_ids:
                # Gọi hàm tổng hợp của mã hàng nếu chưa có
                code._compute_grouped_material_line_ids()
                for line in code.aggregated_material_ids:
                    key = (
                        line.mtr_type.id if line.mtr_type else False,
                        line.mtr_name,
                        line.mtr_code,
                        line.mtr_no,
                        line.dimension,
                        line.color_item,
                        line.color_name,
                        line.color_set,
                        line.color_code,
                        line.rate,
                        line.supplier.id if line.supplier else False,
                    )
                    if key not in group_dict:
                        group_dict[key] = {
                            'order_id': order.id,
                            'position': line.position,
                            'mtr_no': line.mtr_no,
                            'mtr_type': line.mtr_type.id if line.mtr_type else False,
                            'mtr_code': line.mtr_code,
                            'mtr_name': line.mtr_name,
                            'dimension': line.dimension,
                            'color_item': line.color_item,
                            'color_name': line.color_name,
                            'color_set': line.color_set,
                            'color_code': line.color_code,
                            'rate': line.rate,
                            'price': line.price,
                            'supplier': line.supplier.id if line.supplier else False,
                            'country': line.country,
                            'est_qty': 0.0,
                            'act_qty': 0.0,
                        }
                    group_dict[key]['est_qty'] += line.est_qty or 0.0
                    group_dict[key]['act_qty'] += line.act_qty or 0.0

            for vals in group_dict.values():
                SummaryModel.create(vals)

            order.aggregated_material_ids = SummaryModel.search([
                ('order_id', '=', order.id)
            ])
    # ----------- PHẦN 1: Tìm kiếm, import/export MÃ HÀNG -----------
    product_search_text = fields.Char(string='Tìm kiếm mã hàng')
    product_search_active = fields.Boolean(string='Đang tìm mã hàng', default=False)    
    def action_search_product(self):
        self.ensure_one()
        if not self.product_search_text:
            return
        self.product_search_active = True
        return {}

    def clear_search_product(self):
        self.ensure_one()
        self.product_search_text = False
        self.product_search_active = False
        return {}

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
            'res_model': 'product.import.export.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
            },
        }
        
    # ----------- PHẦN 2: Tìm kiếm, import/export VẬT TƯ -----------
    material_search_text = fields.Char(string='Tìm kiếm vật tư')
    material_search_active = fields.Boolean(string='Đang tìm vật tư', default=False)

    def action_search_material(self):
        self.ensure_one()
        if not self.material_search_text:
            return
        self.material_search_active = True
        return {}

    def clear_search_material(self):
        self.ensure_one()
        self.material_search_text = False
        self.material_search_active = False
        return {}

    @api.onchange('material_search_text')
    def _onchange_material_search_text(self):
        if not self.material_search_text and self.material_search_active:
            self.clear_search_material()

    def button_dummy_material(self):
        return True

    def action_import_material(self):
        self.ensure_one()
        return { 
            'type': 'ir.actions.act_window',
            'res_model': 'material.import.export.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,  # self là warehouse.order
            },
        }
   
    def action_export_sum_material(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/export/order/{self.id}',
            'target': 'self',
        }

      
    # Tạo các po gửi nhà cung cấp                
    def action_create_po_from_aggregated_materials(self):
        """
        Tạo PO theo từng nhà cung cấp từ danh sách vật tư đã tổng hợp
        """
        MaterialLine = self.env['material.line']
        PurchaseOrder = self.env['material.purchase.order']

        for order in self:
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
                        'position': line.position,
                        'mtr_no': line.mtr_no,
                        'mtr_type': line.mtr_type.id if line.mtr_type else False,
                        'mtr_code': line.mtr_code,
                        'mtr_name': line.mtr_name,
                        'dimension': line.dimension,
                        'color_item': line.color_item,
                        'color_name': line.color_name,
                        'color_set': line.color_set,
                        'color_code': line.color_code,
                        'est_qty': line.est_qty,
                        'act_qty': line.act_qty,
                        'rate': line.rate,
                        'price': line.price,
                        'supplier': supplier.id,
                        'country': line.country,
                        'cif_price': line.cif_price,
                        'fob_price': line.fob_price,
                        'exwork_price': line.exwork_price,
                    })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': 'Đã tạo PO vật tư theo nhà cung cấp.',
                'type': 'success',
            }
        }
    # Xuất vật tư theo po
    def action_export_po_material(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/export/order_po/{self.id}',
            'target': 'self',
        }  
# endregion
    
#-------------------------------------------------------------   
# region (3)  Tạo các button chuyển trang thay vì mở popup
    # button open đơn hàng -> Mã hàng 

        
    # button open đơn hàng -> danh sách po open_product_code_form


# endregion