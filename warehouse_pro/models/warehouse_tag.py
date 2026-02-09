from odoo import api, fields, models, exceptions, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)

class WarehouseTag(models.Model):
    _name = 'warehouse.tag'
    _description = 'Tag cho kho và kệ'

    name = fields.Char(string="Tag Name", required=True)
    # Tự động gán nhân viên tạo kệ
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)  
        return employee.id if employee else False
    
    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self._get_employee_default(), store=True)
    
    color = fields.Integer(string="Màu sắc")
    _sql_constraints = [('name_uniq', 'unique (name)', "Tag name already exists!")]
    
    description = fields.Text(string="Mô tả")
    active = fields.Boolean(string="hoạt động", default=True)
    sequence = fields.Integer(string="Thứ tự", default=10)

    def success_notification(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': 'Thành công',
                'message': 'Tag mới đã được tạo thành công!',
                'sticky': False,
            },
        }       
    @api.model
    def create(self, vals):
       # self.check_user_access('create')
        tags = super(WarehouseTag, self).create(vals)
        tags.success_notification()
        return tags