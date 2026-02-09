from odoo import models, fields
from odoo.exceptions import ValidationError

import base64
import pandas as pd
import io
import math
import re
from lxml import etree  # nếu dùng ở nơi khác


class MaterialStyleImportWizard(models.TransientModel):
    _name = 'material.style.import.wizard'
    _description = 'Wizard Import Vật Tư theo Style'

    product_code_id = fields.Many2one('product.code', string='Style', required=True)
    order_id = fields.Many2one('warehouse.order', related='product_code_id.warehouse_order_id', string='Chương trình', store=True)
    file = fields.Binary(string='File Excel')
    filename = fields.Char(string='Tên file')

    def action_download_template(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/order_management/static/src/xlsx/import_style_excel/form_material_style_color_size_.xlsx',
            'target': 'self',
        }

    # ---- helper normalize header ----
    def _normalize_header(self, h):
        """ Chuẩn hóa một header:
            - trim
            - chuyển các số float dạng '48.0' -> '48'
            - chuyển các số trong chuỗi như 'Dimension_48.0' -> 'Dimension_48'
        """
        if h is None:
            return ''
        s = str(h).strip()
        # replace numeric occurrences with normalized form
        def repl(m):
            num = m.group(0)
            try:
                f = float(num)
                if math.isfinite(f) and float(int(f)) == f:
                    return str(int(f))
                return num
            except Exception:
                return num
        # regex tìm số (cả integer và float)
        return re.sub(r'\d+\.?\d*', repl, s)
    
    def _normalize_value(self, value):
        if value is None:
            return ''
        return str(value).strip()
    
    def import_excel(self):
        if not self.file:
            raise ValidationError("Vui lòng chọn file Excel trước khi import.")

        try:
            df = pd.read_excel(io.BytesIO(base64.b64decode(self.file)), header=6, engine='openpyxl', dtype=str, na_filter=False)
        except Exception as e:
            raise ValidationError(f"Lỗi đọc file Excel: {e}")

        # Chuẩn hóa header
        df.columns = [self._normalize_header(col) for col in df.columns]
        df.columns = [str(c).strip() for c in df.columns]

        # -------- Lấy danh sách size hệ thống ----------
        size_records = self.env['product.size'].search([])
        size_map = {}
        for s in size_records:
            norm = self._normalize_header(s.name)
            if norm:
                size_map[norm] = s.id
        size_names_norm = sorted(size_map.keys(), key=lambda x: (not x.isdigit(), x))

        # ----- Validate các cột bắt buộc -----
        required_cols = [
            'Color.style#', 'Color.style Name', 'Mtr#', 'Supplier', 'Price'
        ]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValidationError(f"Thiếu các cột sau trong file Excel: {', '.join(missing)}")

        # ----- build models -----
        product_code_model = self.env['product.code']
        product_color_model = self.env['product.color']
        product_color_size_model = self.env['product.color.size']
        program_customer_model = self.env['program.customer']

        warnings = []
        processed_materials = set()

        for idx, row in df.iterrows():
            row_num_display = idx + 7 + 1
            color_name = self._normalize_value(row.get('Color.style Name', ''))
            color_code = self._normalize_value(row.get('Color.style#', ''))

            if not color_name:
                raise ValidationError(f"Dòng {row_num_display}: Thiếu Color Name.")

            # tìm style
            code_rec = product_code_model.search([
                ('name', '=', self.product_code_id.name),
                ('warehouse_order_id', '=', self.product_code_id.warehouse_order_id.id)
            ], limit=1)
            if not code_rec:
                raise ValidationError(f"Dòng {row_num_display}: Không tìm thấy style '{self.product_code_id.name}' trong chương trình.")

            # tìm màu
            color_rec = product_color_model.search([
                ('name', '=', color_name),
                ('color_code', '=', color_code)
            ], limit=1)
            if not color_rec:
                raise ValidationError(f"Dòng {row_num_display}: Không tìm thấy Màu '{color_name}' với mã '{color_code}'.")

            # --- Find program.customer (Material Instance) ---
            mtr_sharp = self._normalize_value(row.get('Mtr#', ''))
            if not mtr_sharp:
                raise ValidationError(f"Dòng {row_num_display}: Thiếu Mtr#.")

            supplier_name = self._normalize_value(row.get('Supplier', ''))
            supplier_sharp = self._normalize_value(row.get('Supplier#', '')) if 'Supplier#' in df.columns else ''

            supplier_id = self._get_supplier_partner(
                supplier_sharp=supplier_sharp,
                supplier_name=supplier_name,
            )
            
            if not supplier_id:
                warnings.append(f"Dòng {row_num_display}: Vật tư với Mtr# '{mtr_sharp}' được import không có nhà cung cấp.")

            # Check for duplicates within the file
            material_key = (mtr_sharp, supplier_id, color_name, color_code)
            if material_key in processed_materials:
                supplier_display = supplier_name or supplier_sharp or 'trống'
                raise ValidationError(f"Dòng {row_num_display}: Lỗi: Vật tư với Mtr# '{mtr_sharp}', Nhà cung cấp '{supplier_display}' và Màu '{color_name} ({color_code})' đã tồn tại ở dòng trước trong file này.")
            processed_materials.add(material_key)

            # Find by Mtr# and Supplier
            program_customer = program_customer_model.search([
                ('name', '=', mtr_sharp),
                ('supplier', '=', supplier_id)
            ], limit=1)

            if not program_customer:
                supplier_display = supplier_name or supplier_sharp or 'trống'
                raise ValidationError(f"Dòng {row_num_display}: Không tìm thấy vật tư với Mtr# '{mtr_sharp}' và Nhà cung cấp '{supplier_display}'. Vui lòng đảm bảo vật tư đã tồn tại trong hệ thống.")

            # Update prices
            price_vals = {
                'price': self._safe_float(row.get('Price')),
            }
            if 'Cif_price' in df.columns:
                price_vals['cif_price'] = self._safe_float(row.get('Cif_price'))
            if 'Fob_price' in df.columns:
                price_vals['fob_price'] = self._safe_float(row.get('Fob_price'))
            if 'Exwork_price' in df.columns:
                price_vals['exwork_price'] = self._safe_float(row.get('Exwork_price'))
            
            program_customer.write(price_vals)

            # ---- Quét toàn bộ size ----
            for s in size_names_norm:
                size_flag_col = f"Size_{s}"
                if size_flag_col not in df.columns:
                    continue

                flag_val = self._normalize_value(row.get(size_flag_col, ''))
                if not flag_val or flag_val in ['-', '0']:  # bỏ qua nếu trống / gạch / 0
                    continue

                size_id = size_map.get(s)
                if not size_id:
                    continue

                # tìm variant
                variant = product_color_size_model.search([
                    ('product_code_id', '=', code_rec.id),
                    ('color_id', '=', color_rec.id),
                    ('size_id', '=', size_id)
                ], limit=1)
                if not variant:
                    raise ValidationError(
                        f"Dòng {row_num_display}: Không tìm thấy style {self.product_code_id.name}-{color_name}-{s}."
                    )

                # Gắn variant vào program_customer
                program_customer.write({
                    'color_size_ids': [(4, variant.id)],
                    'warehouse_order_ids': [(4, self.product_code_id.warehouse_order_id.id)],
                })

                # Norm (consumption)
                cons_col = f"Cons_{s}"
                if cons_col in df.columns:
                    consumption = self._safe_float(row.get(cons_col))
                    if consumption > 0:
                        self._update_or_create_norm_line(program_customer.id, variant.id, consumption)

        message = f"✅ Import vật tư thành công cho style(color,size)."
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

    def _get_supplier_partner(self, supplier_sharp, supplier_name):
        supplier_sharp = str(supplier_sharp or '').strip()
        supplier_name = str(supplier_name or '').strip()

        if not supplier_sharp and not supplier_name:
            return False

        supplier = None
        # Tìm theo Supplier#
        if supplier_sharp:
            supplier = self.env['supplier.partner'].search([('supplier_index', '=', supplier_sharp)], limit=1)

        # Nếu không có, tìm theo Supplier Name
        if not supplier and supplier_name:
            supplier = self.env['supplier.partner'].search([('name_supplier', '=ilike', supplier_name)], limit=1)

        # Nếu vẫn không tìm thấy, tạo mới
        if not supplier:
            if not supplier_name and not supplier_sharp:
                return False
            
            create_vals = {
                'supplier_index': supplier_sharp or supplier_name,
                'name_supplier': supplier_name or supplier_sharp,
            }
            supplier = self.env['supplier.partner'].create(create_vals)

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

    def _update_or_create_norm_line(self, program_customer_id, variant_id, consumption):
        NormLine = self.env['material.norm.line']
        existing = NormLine.search([
            ('program_customer_id', '=', program_customer_id),
            ('color_size_id', '=', variant_id)
        ], limit=1)
        if existing:
            existing.consumption = consumption
        else:
            NormLine.create({
                'program_customer_id': program_customer_id,
                'color_size_id': variant_id,
                'consumption': consumption
            })