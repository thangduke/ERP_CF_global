from odoo import models, fields, api
import base64
import pandas as pd
import tempfile
import os
import datetime
from odoo.exceptions import ValidationError

class MaterialInvoice(models.Model):
    _name = 'material.invoice'
    _description = 'Mã Invoice vật tư'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'
    _order = "create_date desc"
    
    
    name = fields.Char(string="Mã Invoice", required=True)
    @api.model
    def _get_employee_default(self):
        employee = self.env['employee.base'].search([('user_id', '=', self.env.uid)], limit=1)  
        return employee.id if employee else False
    employee_id = fields.Many2one('employee.base', 'Người tạo',
                                  default=lambda self: self._get_employee_default(), store=True)
    
    avatar_name_job = fields.Html(related='employee_id.avatar_name_job', string="Người tạo")
    
    date_create = fields.Datetime(string="Ngày tạo", default=fields.Datetime.now, readonly=True)
    
    order_id = fields.Many2one('warehouse.order', string="Đơn hàng",ondelete='cascade' )
    supplier = fields.Char(string="Nhà cung cấp", help="SUPPLIER")
    invoice_no = fields.Char(string="Mã Invoice nhà cung cấp", required=True, help="INVOICE NO")
    # liên kết với model vật tư
    
    active = fields.Boolean('Active', default=True)
    description = fields.Text('Mô tả')
    description_display = fields.Text('Mô tả', compute='_compute_description_display')

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
    
    def action_export(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/export/material/{self.id}',
            'target': 'self',
        }


    def action_import(self):
        """Action to import materials for the current invoice"""
        self.ensure_one()  # Đảm bảo chỉ có một bản ghi được chọn

        # Tạo wizard để tải file
        return {'''
            'type': 'ir.actions.act_window',
            'res_model': 'material.import.export.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_id': self.id,
            },'''
        }  