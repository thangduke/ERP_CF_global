from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class AssetAsset(models.Model):
    _name = 'asset.asset'
    _description = 'Tài sản chi tiết'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã tài sản này đã được tạo vui lòng nhập mã tài sản khác!'),
        ('serial_number_unique', 'unique(serial_number)', 'Số Serial này đã được tạo vui lòng nhập số Serial khác!')
    ]
    name = fields.Char(string='Tên tài sản', required=True, tracking=True)
    code = fields.Char(string='Mã tài sản', default=lambda self: 'New')
    serial_number = fields.Char(string='Số Serial', tracking=True)
    
    asset_type_id = fields.Many2one('asset.type', string='Chủng loại',  required=True, tracking=True,
                                    domain="[('category_id', '=', category_id)]")
    category_id = fields.Many2one('asset.category',required=True, string='Danh mục', store=True, )
    
    status_color = fields.Char(related='status_id.color', string='Màu trạng thái', )
    status_id = fields.Many2one('asset.status', string='Trạng thái', required=True, tracking=True)
    
    location_id = fields.Many2one('asset.location', string='Chủ sở hữu', required=True, tracking=True)
    
    image_128 = fields.Image("Image", max_width=128, max_height=128, store=True)
    
    purchase_date = fields.Date(string='Ngày mua', tracking=True)
    purchase_value = fields.Float(string='Giá trị mua', tracking=True)
    current_value = fields.Float(string='Giá trị hiện tại', tracking=True)
    
    usage_id = fields.Many2one('asset.usage', string='Đơn vị sử dụng', tracking=True)
    
    attachment_ids = fields.One2many(
        'ir.attachment', 'res_id',
        domain=[('res_model', '=', 'asset.asset')],
        string="File đính kèm"
    )

    manager_id = fields.Many2one('employee.base', string='Người quản lý', tracking=True)
    borrower_id = fields.Many2one('employee.base', string='Người mượn', tracking=True)
    department_id = fields.Many2one('employee.department', 'Vi trí người mượn', related='borrower_id.department_id', store=True, tracking=True, )
    position_id = fields.Many2one('employee.position', 'Vị trí công việc', related='borrower_id.position_id',store=True, tracking=True)
    date_borrow = fields.Date(string='Ngày mượn', tracking=True)
       
    description = fields.Text(string='Mô tả')
    active = fields.Boolean(string='Active', default=True)

    # Thông tin người tạo
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)
        return employee.id if employee else False
    
    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self._get_employee_default(), store=True, readonly=True)
    
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")
    
    date_create = fields.Datetime(string='Ngày tạo', default=fields.Datetime.now, readonly=True)

    activity_history_ids = fields.One2many('asset.activity.history', 'asset_id', string='Lịch sử hoạt động')

    @api.model_create_multi
    def create(self, vals_list):
        assets = super().create(vals_list)
        for asset in assets:
            # if 'code' not in vals_list[0] or vals_list[0].get('code') == 'New':
            #    asset.code = self.env['ir.sequence'].next_by_code('asset.asset') or 'New'
            asset.activity_history_ids.create({
                'asset_id': asset.id,
                'description': 'Tài sản đã được tạo.'
            })
        return assets

    def write(self, vals):
        if 'borrower_id' in vals:
            if vals.get('borrower_id'):
                borrower = self.env['employee.base'].browse(vals['borrower_id'])
                self.activity_history_ids.create({
                    'asset_id': self.id,
                    'description': f'Tài sản được bàn giao cho {borrower.name}.'
                })
            else:
                self.activity_history_ids.create({
                    'asset_id': self.id,
                    'description': 'Tài sản đã được trả lại.'
                })

        if 'status_id' in vals:
            status = self.env['asset.status'].browse(vals['status_id'])
            self.activity_history_ids.create({
                'asset_id': self.id,
                'description': f'Trạng thái của tài sản đã được thay đổi thành "{status.name}".'
            })
        return super().write(vals)