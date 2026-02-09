from odoo import models, fields, api
import base64
import pandas as pd
from odoo.exceptions import ValidationError
import io


class ProductImportExportWizard(models.TransientModel):
    _name = 'product.import.export.wizard'
    _description = 'Wizard Import Style + Color + Size theo Chương trình'

    order_id = fields.Many2one('warehouse.order', string='Chương trình', required=True)
    file = fields.Binary(string="File Excel", )
    filename = fields.Char(string="Tên file")

    def import_excel(self):
        if not self.file:
            raise ValidationError("Vui lòng tải tệp Excel.")

        try:
            # Đọc từ dòng 7 (bỏ qua 6 dòng đầu tiên)
            df = pd.read_excel(io.BytesIO(base64.b64decode(self.file)), skiprows=6, engine='openpyxl', dtype=str)
            df.columns = df.columns.str.strip()
        except Exception as e:
            raise ValidationError(f"Lỗi khi đọc file Excel: {e}")

        # Các cột cần có
        expected_columns = [
            'Buyer PO Info', 'Style Name', 'Color#', 'Color Name',
            'Label', 'Dimpk', 'PPK', 'Size Description', 'Order QTY', 'Test QTY', 'Unit Cost', 'EXT'
        ]
        missing_columns = [col for col in expected_columns if col not in df.columns]
        if missing_columns:
            raise ValidationError(f"Các cột sau đang thiếu trong file Excel: {', '.join(missing_columns)}")

        for index, row in df.iterrows():
            # Lấy dữ liệu từng dòng
            ean_no = str(row.get('Buyer PO Info', '')).strip()
            product_desc = str(row['Style Name']).strip() if not pd.isna(row['Style Name']) else ''
            color_code = str(row['Color#']).strip()
            color_name = str(row['Color Name']).strip()
            label = str(row['Label']).strip() if not pd.isna(row['Label']) else ''
            dimpk = float(row['Dimpk']) if not pd.isna(row['Dimpk']) else 0.0
            ppk = int(row['PPK']) if not pd.isna(row['PPK']) else 0
            size_name = str(row['Size Description']).strip()
            order_qty = float(row.get('Order QTY', 0)) if not pd.isna(row.get('Order QTY', 0)) else 0
            test_qty = float(row.get('Test QTY', 0)) if not pd.isna(row.get('Test QTY', 0)) else 0
            unit_cost = float(row.get('Unit Cost', 0)) if not pd.isna(row.get('Unit Cost', 0)) else 0
            ext = float(row.get('EXT', 0)) if not pd.isna(row.get('EXT', 0)) else 0

            if not color_name or not size_name or not product_desc:
                continue  # Bỏ qua dòng không đủ thông tin

            # Tìm hoặc tạo product.code (tách theo từng mô tả)
            code_rec = self.env['product.code'].search([
                ('warehouse_order_id', '=', self.order_id.id),
                ('ean_no', '=', ean_no),
            ], limit=1)
            if not code_rec:
                code_rec = self.env['product.code'].create({
                    'warehouse_order_id': self.order_id.id,
                    'ean_no': ean_no,
                    'description': product_desc
                })

            # Tìm hoặc tạo color
            color_rec = self.env['product.color'].search([('color_code', '=', color_code)], limit=1)
            if not color_rec:
                color_rec = self.env['product.color'].create({'name': color_name, 'color_code': color_code})

            # Tìm hoặc tạo size
            size_rec = self.env['product.size'].search([('name', '=', size_name)], limit=1)
            if not size_rec:
                size_rec = self.env['product.size'].create({'name': size_name})

            # Tìm hoặc tạo style màu + size
            variant_rec = self.env['product.color.size'].search([
                ('product_code_id', '=', code_rec.id),
                ('color_id', '=', color_rec.id),
                ('size_id', '=', size_rec.id)
            ], limit=1)

            vals = {
                'warehouse_order_id': self.order_id.id,
                'product_code_id': code_rec.id,
                'ean_no': ean_no,
                'description': product_desc,
                'color_id': color_rec.id,
                'color': color_code,
                'size_id': size_rec.id,
                'order_qty': order_qty,
                'test_qty': test_qty,  
                'label': label,
                'dimpk': dimpk,
                'ppk': ppk,
                'unit_cost': unit_cost,
                'ext': ext,
            }
            if order_qty > 0:
                if not variant_rec:
                    self.env['product.color.size'].create(vals)
                else:
                    variant_rec.write(vals)

        message = f"✅ Import danh sách style(color,size) thành công."
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Kết quả',
                'message': message,
                'sticky': False,
                'type': 'success'
            }
        }
        
    def action_download_template(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/order_management/static/src/xlsx/import_progarm_excel/form_style_color_size_.xlsx',
            'target': 'self',
        }