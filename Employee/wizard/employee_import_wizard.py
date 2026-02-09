from odoo import models, fields, _
from odoo.exceptions import UserError
import base64
import pandas as pd
import io

class EmployeeImportWizard(models.TransientModel):
    _name = 'employee.import.wizard'
    _description = 'Wizard Import Nhân sự'

    file = fields.Binary(string='Tải lên File Excel', required=True)
    filename = fields.Char(string='Tên file')

    def action_download_template(self):
        """Hành động trả về URL để tải file template."""
        return {
            'type': 'ir.actions.act_url',
            'url': '/Employee/static/xlsx/Employee_template_import.xlsx',
            'target': 'self',
        }

    def action_import(self):
        """Hành động xử lý import từ file Excel."""
        if not self.file:
            raise UserError(_("Vui lòng tải lên một file để import!"))

        try:
            file_data = base64.b64decode(self.file)
            df = pd.read_excel(io.BytesIO(file_data), dtype=str).fillna('')
            
            column_mapping = {
                'Tài khoản': 'user_email',
                'Mã nhân sự': 'employee_index',
                'Bộ phận': 'department_name',
                'Vị trí công việc': 'position_name',
                'Vị trí công tác': 'position_type_name',
                'Loại nhân sự': 'employee_type_2_name',
                'Ngày bắt đầu': 'start_date',
                'Ngày chính thức': 'official_date',
                'Giới tính': 'gender',
                'Ngày sinh': 'birthday',
                'Số điện thoại': 'mobile_phone',
            }
            df.rename(columns=column_mapping, inplace=True)

            employees_to_create = []
            
            for index, row in df.iterrows():
                vals = {}
                
                # --- Xử lý User (res.users) ---
                user_email = row.get('user_email')
                if not user_email:
                    raise UserError(_("Dòng %s: 'Tài khoản' (email) là bắt buộc.") % (index + 2))

                user = self.env['res.users'].search([('login', '=', user_email)], limit=1)
                if not user:
                    raise UserError(_("Dòng %s: Không tìm thấy tài khoản với email '%s'. Vui lòng tạo tài khoản trước khi import.") % (index + 2, user_email))
                
                vals['user_id'] = user.id
                vals['name'] = user.name # Tự động lấy tên từ user
                vals['work_email'] = user.email # Tự động lấy email từ user
                
                # --- Xử lý các trường quan hệ Many2one ---
                department_name = row.get('department_name')
                if department_name:
                    department = self.env['employee.department'].search([('name', '=', department_name)], limit=1)
                    if not department:
                        raise UserError(_("Dòng %s: Không tìm thấy Bộ phận '%s'. Vui lòng tạo trước trong hệ thống.") % (index + 2, department_name))
                    vals['department_id'] = department.id

                position_name = row.get('position_name')
                if position_name:
                    if not department_name:
                        raise UserError(_("Dòng %s: Cột 'Bộ phận' là bắt buộc khi có 'Vị trí công việc'.") % (index + 2))
                    position = self.env['employee.position'].search([
                        ('name', '=', position_name), 
                        ('department_id', '=', vals.get('department_id'))
                    ], limit=1)
                    if not position:
                        raise UserError(_("Dòng %s: Không tìm thấy Vị trí công việc '%s' trong bộ phận '%s'. Vui lòng tạo trước.") % (index + 2, position_name, department_name))
                    vals['position_id'] = position.id

                position_type_name = row.get('position_type_name')
                if position_type_name:
                    pos_type = self.env['position.type'].search([('name', '=', position_type_name)], limit=1)
                    if not pos_type:
                        raise UserError(_("Dòng %s: Không tìm thấy Vị trí công tác '%s'. Vui lòng tạo trước.") % (index + 2, position_type_name))
                    vals['position_type'] = pos_type.id

                employee_type_2_name = row.get('employee_type_2_name')
                if employee_type_2_name:
                    emp_type = self.env['employee.type'].search([('name', '=', employee_type_2_name)], limit=1)
                    if not emp_type:
                        raise UserError(_("Dòng %s: Không tìm thấy Loại nhân sự '%s'. Vui lòng tạo trước.") % (index + 2, employee_type_2_name))
                    vals['employee_type_2'] = emp_type.id

                # --- Xử lý các trường thông thường ---
                for field in ['employee_index', 'mobile_phone', 'start_date', 'official_date', 'birthday']:
                    if row.get(field):
                        vals[field] = row[field]
                
                gender_map = {'Nam': 'male', 'Nữ': 'female', 'Khác': 'other'}
                if row.get('gender'):
                    vals['gender'] = gender_map.get(row['gender'])

                employees_to_create.append(vals)

            if employees_to_create:
                self.env['employee.base'].create(employees_to_create)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Thành công'),
                    'message': _('Đã import thành công %s nhân sự.') % len(employees_to_create),
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            raise UserError(_("Đã có lỗi xảy ra trong quá trình import: %s") % e)