import base64
import io
import datetime
from odoo import http
from odoo.http import request
import xlsxwriter

class XntReportExport(http.Controller):

    @http.route('/export/xnt_report', type='http', auth='user')
    def export_xnt_report(self, **kwargs):
        # Lấy các tham số từ request
        store_id = kwargs.get('store_id')
        start_date = kwargs.get('start_date')
        end_date = kwargs.get('end_date')

        # Chuẩn bị các bộ lọc
        filters = {
            'page': 'page3',
            'filter_store_id': store_id,
            'start_date': start_date,
            'end_date': end_date,
        }

        # Gọi phương thức để lấy dữ liệu báo cáo
        report_data = request.env['warehouse.dashboard'].get_dashboard_data(filters)
        report_lines = report_data.get('lines', [])

        # Tạo file Excel
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet()

        # Styles

        # Styles
        report_title_format = workbook.add_format({
            'bold': True, 'font_size': 16, 'align': 'center', 'valign': 'vcenter', 'font_name': 'Times New Roman'
        })
        date_format = workbook.add_format({
            'align': 'center', 'valign': 'vcenter', 'font_name': 'Times New Roman', 'font_size': 11
        })
        header_format = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#DDEBF7', 'border': 1,
            'font_name': 'Times New Roman', 'font_size': 12, 'text_wrap': True
        })
        text_format = workbook.add_format({
            'align': 'left', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman', 'font_size': 11, 'text_wrap': True
        })
        number_format = workbook.add_format({
            'align': 'right', 'border': 1, 'num_format': '#,##0', 'font_name': 'Times New Roman', 'font_size': 11, 'valign': 'vcenter'
        })
        price_format = workbook.add_format({
            'align': 'right', 'border': 1, 'num_format': '#,##0.00', 'font_name': 'Times New Roman', 'font_size': 11, 'valign': 'vcenter'
        })
        stt_format = workbook.add_format({
            'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman', 'font_size': 11
        })

        # Dynamic row tracking
        row = 0

        # Report Header
        worksheet.merge_range(row, 0, row, 12, "BÁO CÁO TỔNG HỢP NHẬP XUẤT TỒN", report_title_format)
        worksheet.set_row(row, 30)
        row += 1
        
        today = datetime.date.today()
        worksheet.merge_range(row, 0, row, 12, f"Ngày {today.day} tháng {today.month} năm {today.year}", date_format)
        row += 1

        if start_date and end_date:
            worksheet.merge_range(row, 0, row, 12, f"Từ ngày {start_date} đến ngày {end_date}", date_format)
            row += 1


        # Ghi header
        headers = [
            "STT", "Mtr#", "Mtr_code", "Mtr Type", "Unit", "Dimension", "Color#", "Color name",
            "Supplier", "Price $", "SL Tồn đầu", "Dư đầu", "SL Nhập", "Tiền nhập $", "SL Xuất", "Tiền xuất $", "SL Tồn cuối", "Dư cuối $"
        ]
        for col_num, header in enumerate(headers):
            worksheet.write(row, col_num, header, header_format)
        # Set column widths
        worksheet.set_column('A:A', 5)
        worksheet.set_column('B:B', 20)
        worksheet.set_column('C:C', 20)
        worksheet.set_column('D:D', 12)
        worksheet.set_column('E:E', 10)
        worksheet.set_column('F:F', 15)
        worksheet.set_column('G:G', 15)
        worksheet.set_column('H:H', 20)
        worksheet.set_column('I:I', 20)
        worksheet.set_column('J:R', 12)   
             
        data_start_row = row + 1

        # Ghi dữ liệu
        for idx, line in enumerate(report_lines):
            current_row = data_start_row + idx
            stt = idx + 1
            worksheet.write(current_row, 0, stt, stt_format)
            worksheet.write(current_row, 1, line.get('material_name', ''), text_format)
            worksheet.write(current_row, 2, line.get('material_code', ''), text_format)
            
            worksheet.write(current_row, 3, line.get('mtr_type', ''), text_format)

            worksheet.write(current_row, 4, line.get('material_unit', ''), text_format)
            
            worksheet.write(current_row, 5, line.get('dimension', ''),  text_format)
            
            worksheet.write(current_row, 6, line.get('color_item', ''), text_format)
            worksheet.write(current_row, 7, line.get('color_name', ''), text_format)
            
            worksheet.write(current_row, 8, line.get('supplier', ''), text_format)


            worksheet.write(current_row, 9, line.get('price', 0), price_format)
            worksheet.write(current_row, 10, line.get('opening_qty', 0), number_format)
            worksheet.write(current_row, 11, line.get('value_open', 0.00), price_format)
            
            worksheet.write(current_row, 12, line.get('qty_in', 0), number_format)
            worksheet.write(current_row, 13, line.get('value_in', 0.00), price_format)
            
            worksheet.write(current_row, 14, line.get('qty_out', 0), number_format)
            worksheet.write(current_row, 15, line.get('value_out', 0.00), price_format)
            
            worksheet.write(current_row, 16, line.get('ending_qty', 0), number_format)
            worksheet.write(current_row, 17, line.get('value_close', 0.00), price_format)

        workbook.close()
        output.seek(0)

        # Trả về file Excel
        filename = f"BaoCao_NXT_{datetime.date.today().strftime('%Y%m%d')}.xlsx"
        response = request.make_response(
            output.read(),
            [
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename="{filename}"')
            ]
        )
        return response