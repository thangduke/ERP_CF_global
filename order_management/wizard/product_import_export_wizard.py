from odoo import models, fields, api
import base64
import pandas as pd
from odoo.exceptions import ValidationError
import io


class ProductImportExportWizard(models.TransientModel):
    _name = 'product.import.export.wizard'
    _description = 'Wizard Import Mã Hàng + Color + Size theo Đơn Hàng'

    order_id = fields.Many2one('warehouse.order', string='Đơn hàng', required=True)
    file = fields.Binary(string="File Excel", )
    filename = fields.Char(string="Tên file")

    def import_excel(self):
        if not self.file:
            raise ValidationError("Vui lòng tải tệp Excel.")

        try:
            df = pd.read_excel(io.BytesIO(base64.b64decode(self.file)), skiprows=11, engine='openpyxl')
            df.columns = df.columns.str.strip()  # Loại bỏ khoảng trắng ở đầu/cuối tên cột
        except Exception as e:
            raise ValidationError(f"Lỗi khi đọc file Excel: {e}")

        # Kiểm tra tên cột cần thiết
        expected_columns = [
            'product code', 'product code descriptions', 'Color', 'Color Name',
            'Label', 'Dimpk', 'PPK', 'Size Description', 'PO Qty'
        ]
        missing_columns = [col for col in expected_columns if col not in df.columns]
        if missing_columns:
            raise ValidationError(f"Các cột sau đang thiếu trong file Excel: {', '.join(missing_columns)}")

        for index, row in df.iterrows():
            product_code = str(row['product code']).strip()
            product_desc = str(row['product code descriptions']).strip() if not pd.isna(row['product code descriptions']) else ''
            color_code = str(row['Color']).strip()
            color_name = str(row['Color Name']).strip()
            label = str(row['Label']).strip() if not pd.isna(row['Label']) else ''
            dimpk = float(row['Dimpk']) if not pd.isna(row['Dimpk']) else 0.0
            ppk = int(row['PPK']) if not pd.isna(row['PPK']) else 0
            size_name = str(row['Size Description']).strip()
            po_qty = int(row['PO Qty']) if not pd.isna(row['PO Qty']) else 0

            if not product_code or not color_name or not size_name:
                continue  # Bỏ qua dòng không đủ dữ liệu

            # Tạo hoặc tìm product.code
            code_rec = self.env['product.code'].search([
                ('name', '=', product_code),
                ('warehouse_order_id', '=', self.order_id.id)
            ], limit=1)
            if not code_rec:
                code_rec = self.env['product.code'].create({
                    'name': product_code,
                    'warehouse_order_id': self.order_id.id,
                    'description': product_desc
                })

            # Tạo hoặc tìm màu
            color_rec = self.env['product.color'].search([('name', '=', color_name)], limit=1)
            if not color_rec:
                color_rec = self.env['product.color'].create({'name': color_name})

            # Tạo hoặc tìm size
            size_rec = self.env['product.size'].search([('name', '=', size_name)], limit=1)
            if not size_rec:
                size_rec = self.env['product.size'].create({'name': size_name})

            # Tạo hoặc cập nhật dòng màu + size
            variant_rec = self.env['product.color.size'].search([
                ('product_code_id', '=', code_rec.id),
                ('color_id', '=', color_rec.id),
                ('size_id', '=', size_rec.id)
            ], limit=1)

            vals = {
                'warehouse_order_id': self.order_id.id,
                'product_code_id': code_rec.id,
                'color_id': color_rec.id,
                'color': color_code,
                'size_id': size_rec.id,
                'quantity': po_qty,
                'po_qty': po_qty,
                'label': label,
                'dimpk': dimpk,
                'ppk': ppk,
            }

            if not variant_rec:
                self.env['product.color.size'].create(vals)
            else:
                variant_rec.write(vals)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': 'Đã nhập mã hàng, mô tả, màu, size và thông tin PO!',
                'type': 'success',
                'sticky': False,
            }
        }
        
    def action_download_template(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/order_management/static/src/xlsx/import_excel/Form_Style_Color_Size.xlsx',
            'target': 'self',
        }