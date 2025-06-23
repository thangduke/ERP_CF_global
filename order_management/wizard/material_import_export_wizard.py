from odoo import models, fields
from odoo.exceptions import ValidationError
import base64
import pandas as pd
import io
import math

class MaterialImportExportWizard(models.TransientModel):
    _name = 'material.import.export.wizard'
    _description = 'Wizard Import Vật Tư theo Đơn hàng - Mã hàng - Màu - Size'

    order_id = fields.Many2one('warehouse.order', string='Đơn hàng', required=True)
    file = fields.Binary(string='File Excel', )
    filename = fields.Char(string='Tên file')
    def action_download_template(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/order_management/static/src/xlsx/import_excel/Form_Material_Style_Color_Size.xlsx',
            'target': 'self',
        }
        
    def import_excel(self):
        if not self.file:
            raise ValidationError("Vui lòng chọn file Excel trước khi import.")

        try:
            df = pd.read_excel(io.BytesIO(base64.b64decode(self.file)), header=9, engine='openpyxl')
            df.columns = df.columns.str.strip()

        except Exception as e:
            raise ValidationError(f"Lỗi đọc file Excel: {e}")

        required_cols = ['product code', 'Color Name', 'Size', 'Type', 'Material name',
                         'Mtr.Code', 'Mtr#', 'Dimension', 'Color#', 'Color name', 'Color set',
                         'Color code', 'Rate', 'Price', 'Supplier', 'Est.Total', 'P/O Total']

        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValidationError(f"Thiếu các cột sau trong file Excel: {', '.join(missing)}")

        for idx, row in df.iterrows():
            product_code = str(row['product code']).strip()
            color_name = str(row['Color Name']).strip()
            size_name = str(row['Size']).strip()

            if not product_code or not color_name or not size_name:
                raise ValidationError(
                    f"Dòng {idx + 9}: Thiếu thông tin bắt buộc (Mã hàng: '{product_code}', Màu: '{color_name}', Size: '{size_name}').")

            code_rec = self.env['product.code'].search([
                ('name', '=', product_code),
                ('warehouse_order_id', '=', self.order_id.id)
            ], limit=1)
            if not code_rec:
                raise ValidationError(f"Không tìm thấy mã hàng '{product_code}' trong đơn hàng.")

            color_rec = self.env['product.color'].search([('name', '=', color_name)], limit=1)
            size_rec = self.env['product.size'].search([('name', '=', size_name)], limit=1)
            if not color_rec or not size_rec:
                raise ValidationError(f"Không tìm thấy Màu '{color_name}' hoặc Size '{size_name}' trong hệ thống.")

            variant = self.env['product.color.size'].search([
                ('product_code_id', '=', code_rec.id),
                ('color_id', '=', color_rec.id),
                ('size_id', '=', size_rec.id)
            ], limit=1)
            if not variant:
                raise ValidationError(f"Không tìm thấy biến thể cho mã hàng '{product_code}' với màu '{color_name}' và size '{size_name}'.")

            material_vals = {
                'color_size_id': variant.id,
                'warehouse_material_id': self.order_id.id,  # Thêm dòng này
                'mtr_type': self._get_material_type(row['Type']),
                'mtr_name': str(row['Material name']).strip(),
                'mtr_code': str(row['Mtr.Code']).strip(),
                'mtr_no': str(row['Mtr#']).strip(),
                'dimension': str(row['Dimension']).strip(),
                'material_color_id': self._get_material_color(
                    color_item=str(row['Color#']).strip(),
                    color_name=str(row['Color name']).strip(),
                    color_set=str(row['Color set']).strip(),
                    color_code=str(row['Color code']).strip()
                ),
                'rate': str(row['Rate']).strip(),
                'price': self._safe_float(row['Price']),
                'supplier': self._get_supplier_partner(str(row['Supplier']).strip()),
                'est_qty': self._safe_float(row['Est.Total']),
                'act_qty': self._safe_float(row['P/O Total']),
            }
            existing = self.env['program.customer'].search([
                ('color_size_id', '=', variant.id),
                ('mtr_code', '=', material_vals['mtr_code']),
                ('mtr_name', '=', material_vals['mtr_name']),
                ('mtr_no', '=', material_vals['mtr_no']),
            ], limit=1)

            if existing:
                existing.write(material_vals)  # Cập nhật lại số lượng và thông tin
            else:
                self.env['program.customer'].create(material_vals)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': 'Đã import vật tư thành công.',
                'type': 'success',
                'sticky': False
            }
        }

    def _get_material_type(self, type_name):
        if not type_name:
            return False
        type_name = str(type_name).strip()
        material_type = self.env['material.type'].search([('name', '=', type_name)], limit=1)
        if not material_type:
            material_type = self.env['material.type'].create({
                'name': type_name,
                'name_type': type_name  # ⚠️ cần truyền vì là bắt buộc
            })
        return material_type.id


    def _get_material_color(self, color_item, color_name, color_set, color_code):
        ColorSet = self.env['material.color.set']
        MaterialColor = self.env['material.color']

        color_set_rec = ColorSet.search([('name', '=', color_set)], limit=1)
        if not color_set_rec and color_set:
            color_set_rec = ColorSet.create({'name': color_set})

        domain = [
            ('name', '=', color_item),  # ✅ sửa đúng field tồn tại
            ('color_name', '=', color_name),
            ('color_code', '=', color_code),
        ]
        if color_set_rec:
            domain.append(('color_set_id', '=', color_set_rec.id))

        color_rec = MaterialColor.search(domain, limit=1)

        if not color_rec:
            color_rec = MaterialColor.create({
                'name': color_item,
                'color_name': color_name,
                'color_code': color_code,
                'color_set_id': color_set_rec.id if color_set_rec else False
            })

        return color_rec.id

    def _get_supplier_partner(self, name):
        if not name:
            return False
        supplier = self.env['supplier.partner'].search([('name', '=', name)], limit=1)
        if not supplier:
            supplier = self.env['supplier.partner'].create({'name': name})
        return supplier.id

    def _safe_float(self, val):
        try:
            if isinstance(val, str):
                val = val.replace(',', '.')
            fval = float(val)
            if math.isnan(fval):
                return 0.0
            return fval
        except (ValueError, TypeError):
            return 0.0
