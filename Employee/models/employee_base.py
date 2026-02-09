from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _


class EmployeeBase(models.Model):
    _name = "employee.base"
    _description = "Nhân sự"
    _inherit = ['avatar.mixin', 'mail.thread.main.attachment']
    
    name = fields.Char(string="Họ và tên", store=True, tracking=True)
    
    employee_index = fields.Char(string='Mã nhân sự', unique=True,  tracking=True)
    
    department_id = fields.Many2one('employee.department', 'Bộ phận', tracking=True, ondelete='set null')
    
    position_id = fields.Many2one('employee.position', 'Vị trí công việc',
                                  domain="[('department_id', '=', department_id)]", tracking=True)
    
    position_type = fields.Many2one('position.type', 'Vị trí công tác', store=True)
    
    job_title = fields.Char(string="Chức danh", related="position_id.name") 
    position_title = fields.Char(string="Chức danh", related="position_id.name")
    
    user_id = fields.Many2one('res.users', required=True, string='Tài khoản', ondelete='cascade')
    
    employee_user_ids = fields.Many2many('res.users', compute='_compute_employee_user_ids',
                                        store=False)
    parent_id = fields.Many2one('employee.base', string="Quản lý (M1)", tracking=True,
                                domain=[('state', '!=', 'quit')], ondelete='set null')
    
    parent_display = fields.Html(related='parent_id.avatar_name_job')
    
    parent_ids = fields.Many2many('employee.base',
                                  'employee_manager_rel', 'employee_id', 'manager_id',
                                  string="Quản lý", tracking=True, domain=[('state', '!=', 'quit')])
    
    child_ids = fields.One2many('employee.base', 'parent_id', string="Cấp dưới",
                                domain=[('state', '!=', 'quit')])    
    subordinate_ids = fields.Many2many('employee.base',
                                       'employee_manager_rel', 'manager_id', 'employee_id',
                                       string="Nhân viên", domain=[('state', '!=', 'quit')])
    
    work_email = fields.Char('Email', store=True, tracking=True)
    work_phone = fields.Char('Số điện thoại công việc', tracking=True)
    mobile_phone = fields.Char('Số điện thoại', tracking=True)
    start_date = fields.Date(string="Ngày bắt đầu", tracking=True)
    official_date = fields.Date(string='Ngày chính thức', tracking=True)
    quit_date = fields.Date('Ngày nghỉ việc')
    full_work_time = fields.Char('Thời gian làm việc', compute='_compute_full_work_time') 
    latest_employee_index = fields.Char(string="Mã nhân sự gần nhất", compute='_compute_latest_employee_index', store=False)
    
    is_manager = fields.Boolean(string="Là quản lý?", default=False)
    nationality = fields.Many2one('res.country', string="Quốc tịch", tracking=True)
    
    identification_id = fields.Char(string='Căn cước công dân', size=12, tracking=True)
    current_address = fields.Char('Địa chỉ hiện tại', tracking=True)
    place_of_birth = fields.Char('Nơi sinh', tracking=True)
    permanent_address = fields.Char('Địa chỉ thường trú', tracking=True)

    gender = fields.Selection([
        ('male', 'Nam'),
        ('female', 'Nữ'),
        ('other', 'Khác')], string='Giới tính', tracking=True)
    birthday = fields.Date('Ngày sinh', tracking=True)
 
    
    employee_type_2 = fields.Many2one('employee.type', 'Phân loại nhân sự', tracking=True, ondelete='set null')

    employee_properties = fields.Properties('Properties 3C',
                                              definition='department_id.employee3c_properties_definition',
                                              precompute=False)


    make_visible = fields.Boolean(string="User", compute='get_user')
    make_visible2 = fields.Boolean(string="User", compute='get_user2')
    make_visible3 = fields.Boolean(string="User", compute='get_user3')
    
    user_name = fields.Char(string="Họ và tên", related='user_id.name', store=False)
    user_mail = fields.Char(string='Email', related='user_id.email', store=False)
    state = fields.Selection(selection=[('probation', 'Đang thử việc'),
                                        ('official', 'Chính thức'),
                                        ('quit', 'Đã nghỉ việc'),
                                        ('break', 'Đang tạm nghỉ')],
                             default='official', string="Tình trạng làm việc", tracking=True)

    company_id = fields.Many2one(related='user_id.company_id')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    user_image = fields.Image(related='user_id.image_1920', store=True)
    image_1920 = fields.Image(related='user_id.image_1920', store=True)

    avatar_name = fields.Html(compute='_compute_avatar_name', string="Avatar & Name")
    avatar_name_job = fields.Html(compute='_compute_avatar_name_job', string="Avatar & Name & Job")

    _sql_constraints = [
        ('check_employee', 'UNIQUE(work_email)', 'Đã tồn tại địa chỉ email này. Địa chỉ email phải là duy nhất!'),
        ('check_id', 'UNIQUE(identification_id)', 'Số căn cước công dân phải là duy nhất '),
        ('identification_id_length_check',
         "CHECK (char_length(identification_id) = 12)",
         "Số căn cước công dân phải bao gồm 12 kí tự."),
        ('check_employee_index', 'UNIQUE(employee_index)', 'Đã tồn tại mã nhân sự này')]
        
    @api.depends('name', 'image_1920')
    def _compute_avatar_name(self):
        for record in self:
            avatar_url = "/web/image/employee.base/%s/image_1920" % record.id
            record.avatar_name = '''
                <div>
                    <img src="%s" style="width: 23px; height: 23px; border-radius: 50%%; margin-right: 7px;"/>
                    <span><b>%s</b></span>
                </div>
            ''' % (avatar_url, record.name)
    
    def _compute_avatar_name_job(self):
        for record in self:
            avatar_url = "/web/image/employee.base/%s/image_1920" % record.id
            record.avatar_name_job = '''
                <div class="d-flex">
                            <div class="mr-3" style="display: flex; align-items: center;">
                                <img src="%s" style="width: 35px; height: 35px; border-radius: 50%%; margin-right: 7px;"/>
                            </div>
                            <div style="flex-grow: 1; padding-left: 10px; display: flex; align-items: center;">
                                <div style="flex: 1; text-align: left;">
                                    <span>
                                        <span style="margin-bottom: 2px; font-weight: bold;font-size:14px;">%s</span>
                                        <br/>
                                        <span style="color: gray; font-size:12px;">%s</span> . <span style="color: gray; font-size:12px;">%s</span>
                                    </span>
                                </div>
                            </div>
                       </div>
            ''' % (avatar_url, record.name, record.employee_index, record.job_title)

    @api.onchange('is_manager')
    def _compute_latest_employee_index(self):
        for record in self:
            if record.is_manager:
                prefix = 'M'
            else:
                prefix = 'S'
            last_employee = self.search([('employee_index', 'like', f'{prefix}%')], order='employee_index desc',
                                        limit=1)
            if last_employee:
                record.latest_employee_index = f"Gợi ý: Mã nhân sự gần nhất là {last_employee.employee_index}"
            else:
                record.latest_employee_index = "Gợi ý: Chưa có mã nhân sự nào trước đó."
                
    @api.depends('start_date', 'quit_date')
    def _compute_full_work_time(self):
        for employee in self:
            if employee.start_date:
                start_date = employee.start_date
                end_date = employee.quit_date if employee.quit_date else fields.Date.today()
                delta = relativedelta(end_date, start_date)
                years = delta.years
                months = delta.months
                days = delta.days
                if years > 0:
                    if months > 0:
                        if days > 0:
                            employee.full_work_time = f"{years} năm {months} tháng {days} ngày làm việc"
                        else:
                            employee.full_work_time = f"{years} năm {months} tháng làm việc"
                    else:
                        employee.full_work_time = f"{years} năm {days} ngày làm việc"
                else:
                    if months > 0:
                        employee.full_work_time = f"{months} tháng {days} ngày làm việc"
                    else:
                        employee.full_work_time = f"{days} ngày làm việc"
            else:
                employee.full_work_time = "Chưa có ngày bắt đầu"
                
    @api.onchange('user_id')
    def _compute_mail(self):
        for employee in self:
            employee.work_email = employee.user_id.email

    @api.onchange('user_id')
    def _compute_name(self):
        for employee in self:
            employee.name = employee.user_id.name

    @api.onchange('user_id')
    def _compute_avatar_employee(self):
        for employee in self:
            employee.image_1920 = self.user_id.image_1920

    # --------------
    @api.depends('make_visible')
    def get_user(self, ):
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        if res_user.has_group('Employee.group_cf_admin'):
            self.make_visible = True
        else:
            self.make_visible = False

    @api.depends('user_id')
    def get_user2(self):
        if self.user_id == self.env.user:
            self.make_visible2 = True
        else:
            self.make_visible2 = False

    @api.depends('make_visible3')
    def get_user3(self, ):
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        if res_user.has_group('Employee.group_cf_manager'):
            self.make_visible3 = True
        else:
            self.make_visible3 = False
    # ------------------

    def action_open_change_wizard(self):
        action = self.env['ir.actions.actions']._for_xml_id('Employee.change_employee_main_info')
        action['context'] = {'default_employee_id': self.id, 'default_user_id': self.user_id.id}
        return action

    def action_change_extra_info(self):
        action = self.env['ir.actions.actions']._for_xml_id('Employee.change_employee_extra_info')
        action['context'] = {'default_employee_id': self.id}
        return action

    def action_change_managers(self):
        action = self.env['ir.actions.actions']._for_xml_id('Employee.change_managers')
        action['context'] = {'default_employee_id': self.id}
        return action

    def action_employee_break(self):
        """Chuyển trạng thái nhân sự sang 'break' (tạm nghỉ)"""
        for record in self:
            record.state = 'break'
            record.message_post(body=f"{self.env.user.name} đã chuyển trạng thái nhân sự {record.name} sang tạm nghỉ.")

    def action_employee_quit(self):
        """Chuyển trạng thái nhân sự sang 'quit' (thôi việc)"""
        for record in self:
            record.state = 'quit'
            record.message_post(body=f"{self.env.user.name} đã chuyển trạng thái nhân sự {record.name} sang thôi việc.")

    def action_employee_working(self):
        """Chuyển trạng thái nhân sự sang 'official' (quay lại làm việc)"""
        for record in self:
            record.state = 'official'
            record.message_post(body=f"{self.env.user.name} đã chuyển trạng thái nhân sự {record.name} quay lại làm việc.")

    @api.model
    def action_open_employee_personal_form(self):
        # Lấy user hiện tại
        current_user = self.env.user

        # Tìm employee liên kết với user hiện tại
        employee = self.env['employee.base'].search([('user_id', '=', current_user.id)], limit=1)

        if employee:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Personal Employee Form',
                'res_model': 'employee.base',
                'view_mode': 'form',
                'res_id': employee.id,  # Mở form của employee tương ứng
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window_close',
            }

    @api.depends('user_id')
    def _compute_employee_user_ids(self):
        for record in self:
            employee_users = self.env['employee.base'].search([('user_id', '!=', False)]).mapped(
                'user_id.id')
            record.employee_user_ids = employee_users


    def action_edit_main_info(self):
        return {
            'name': _('Sửa thông tin công việc'),
            'type': 'ir.actions.act_window',
            'res_model': 'change.main.info',
            'view_mode': 'form',
            'target': 'new',
            'context': dict(self._context, **{
                'default_employee_id': self.id,
                'default_user_id': self.user_id.id
            })
        }

    def action_edit_extra_info(self):
        return {
            'name': _('Sửa thông tin cá nhân'),
            'type': 'ir.actions.act_window',
            'res_model': 'change.extra.info',
            'view_mode': 'form',
            'target': 'new',
            'context': dict(self._context, **{
                'default_employee_id': self.id,
                'default_user_id': self.user_id.id
            })
        }


    @api.model
    def update_employee_state(self):
        today = fields.Date.today()

        employees = self.search([('state', '=', 'break'), ('break_end_date', '<', today)])
        for employee in employees:
            employee.state = 'official'

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Template để nhập thông tin nhân sự'),
            'template': '/Employee/static/xlsx/Employee_template_import.xlsx'
        }]

    def _creation_message(self):
        self.ensure_one()
        doc_name = self.create_uid.name
        return _('%s đã tạo hồ sơ nhân sự.', doc_name)

    def write(self, vals):
        changes = []
        
        personal_fields = ['mobile_phone', 'name', 'nationality', 'identification_id',
                           'permanent_address', 'current_address',
                           'gender', 'birthday']
                           
        job_fields = ['position_id', 'start_date', 'official_date', 'department_id','employee_type_2',
                      'parent_id', 'work_email', 'employee_index']
                      


        for field in personal_fields:
            if field in vals and getattr(self, field) != vals[field]:
                changes.append("thông tin cá nhân")
                break

        for field in job_fields:
            if field in vals and getattr(self, field) != vals[field]:
                changes.append("thông tin công việc") 
                break


        res = super(EmployeeBase, self).write(vals)

        if changes:
            unique_changes = set(changes)  
            change_message = ", ".join(unique_changes)  
            self.message_post(body=f"{self.env.user.name} đã cập nhật {change_message}.")
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super(EmployeeBase, self).create(vals_list)
        if self.env.context.get('import_file', False):
            for record in records:
                message = f"{self.env.user.name} đã tạo hồ sơ nhân sự cho {record.name}."
                record.message_post(body=message)
        return records

    @api.depends('birthday')
    def _compute_birthday_month(self):
        for record in self:
            if record.birthday:
                # Get month as number (1-12) from birthday date
                record.birthday_month = record.birthday.month
            else:
                record.birthday_month = False

    birthday_month = fields.Integer(string='Tháng sinh', compute='_compute_birthday_month', store=True)

    search_name = fields.Char(string="Search Name", compute='_compute_search_name', search='_search_search_name')

    def _compute_search_name(self):
        for record in self:
            record.search_name = ''

    def _search_search_name(self, operator, value):
        domain = [
            '|', '|',  
            ('name', operator, value),
            ('job_title', operator, value),
            ('department_id', operator, value),
        ]
        return domain