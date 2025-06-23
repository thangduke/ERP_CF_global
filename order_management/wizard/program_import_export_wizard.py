# models/material_import_export_wizard.py
from odoo import models, fields, api
import base64
import pandas as pd
from odoo.exceptions import ValidationError


class ProgramImportExportWizard(models.TransientModel):
    _name = 'program.import.export.wizard'
    _description = 'Wizard Import Vật Tư Định Mức'

    file = fields.Binary(string="File Excel", required=True, help="Tải lên file Excel chứa thông tin vật tư định mức.")
    filename = fields.Char(string="Tên file")

    def import_excel(self):
        if not self.file:
            raise ValidationError("Vui lòng tải tệp lên.")

        try:
            df = pd.read_excel(base64.b64decode(self.file), engine='openpyxl')
        except Exception as e:
            raise ValidationError(f"Lỗi khi đọc file Excel: {e}")

        for index, row in df.iterrows():
            try:
                # Tìm hoặc tạo loại vật tư (mtr_type)
                mtr_type_name = row.get('Type')
                mtr_type = None
                if mtr_type_name:
                    mtr_type = self.env['material.type'].search([('name', '=', mtr_type_name)], limit=1)

                        
                self.env['program.customer'].create({
                    'position': row.get('Position') if pd.notna(row.get('Position')) else '',
                    'mtr_type': mtr_type.id if mtr_type else False,
                    'mtr_no': row.get('Mtr#') if pd.notna(row.get('Mtr#')) else '',
                    'mtr_code': row.get('Mtr.Code') if pd.notna(row.get('Mtr.Code')) else '',
                    'mtr_name': row.get('Material Name') if pd.notna(row.get('Material Name')) else '',
                    'dimension': row.get('Dimens.') if pd.notna(row.get('Dimens.')) else '',
                    'color_item': row.get('Shell/Color_item') if pd.notna(row.get('Shell/Color_item')) else '',
                    'color_name': row.get('Shell/Color_name') if pd.notna(row.get('Shell/Color_name')) else '',
                    'est_qty': row.get('Est_qty') if pd.notna(row.get('Est_qty')) else 0.0,
                    'act_qty': row.get('Act_qty') if pd.notna(row.get('Act_qty')) else 0.0,
                    'rate': row.get('Rate')     if pd.notna(row.get('Rate')) else '',
                    'price': row.get('Price') if pd.notna(row.get('Price')) else 0.0,
                    'supplier': row.get('Supplier') if pd.notna(row.get('Supplier')) else '',
                    'country': row.get('Country') if pd.notna(row.get('Country')) else '',
                    'cif_price': row.get('Cif Price') if pd.notna(row.get('Cif Price')) else 0.0,
                    'fob_price': row.get('FOB price') if pd.notna(row.get('FOB price')) else 0.0,
                    'exwork_price': row.get('Exwork price') if pd.notna(row.get('Exwork price')) else 0.0,
                    'total': row.get('TOTAL') if pd.notna(row.get('TOTAL')) else 0.0,
                })
            except Exception as e:
                raise ValidationError(f"Lỗi tại dòng {index + 1}: {e}")
