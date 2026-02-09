from odoo import models, fields, api
from datetime import date

class WarehouseDashboard(models.AbstractModel):
    _name = 'warehouse.dashboard'
    _description = 'Warehouse Dashboard Data Provider'

    @api.model
    def get_dashboard_data(self, filters=None):
        """
        Main entry point for the dashboard to fetch all necessary data based on filters.
        The front-end determines which page to show ('page1' for Warehouse, 'page2' for Program).
        """
        if filters is None:
            filters = {}
        
        page = filters.get('page', 'page1')

        if page == 'page1':  # NXT-Kho (Warehouse View)
            return {
                'kpis': self._get_warehouse_kpis(filters),
                'stock_list': self._get_warehouse_stock_list(filters),
                'available_shelves': self._get_available_shelves(filters),
                'available_shelf_levels': self._get_available_shelf_levels(filters),
            }
        elif page == 'page2':  # NXT-CT (Program View)
            return {
                'kpis': self._get_program_kpis(filters),
                'order_list': self._get_program_stock_list(filters),
            }
        elif page == 'page3':  # XNT Report
            return self.get_xnt_report(filters)
        return {}

# region Page 1: Warehouse View ('NXT-Kho')
    def _get_warehouse_kpis(self, filters):
        """
        KPIs for the Warehouse view:
        - total_materials: Count of unique materials in stock.
        - total_quantity: Total quantity of all materials in stock.
        """
        domain = []
        if filters.get('filter_store_id'):
            domain.append(('store_id', '=', int(filters['filter_store_id'])))
        if filters.get('filter_shelf_id'):
            domain.append(('shelf_id', '=', int(filters['filter_shelf_id'])))
        if filters.get('filter_shelf_level_id'):
            domain.append(('shelf_level_id', '=', int(filters['filter_shelf_level_id'])))
            
        summary_records = self.env['material.stock.summary'].search(domain)

        total_materials = len(summary_records)
        total_quantity = sum(summary_records.mapped('qty_closing'))

        return {
            'total_materials': total_materials,
            'total_quantity': total_quantity,
        }

    def _get_warehouse_stock_list(self, filters):
        """
        Fetches stock data from 'material.stock.summary' for the warehouse view.
        """
        domain = []
        if filters.get('filter_store_id'):
            domain.append(('store_id', '=', int(filters['filter_store_id'])))
        if filters.get('filter_shelf_id'):
            domain.append(('shelf_id', '=', int(filters['filter_shelf_id'])))
        if filters.get('filter_shelf_level_id'):
            domain.append(('shelf_level_id', '=', int(filters['filter_shelf_level_id']))) 
                   
        records = self.env['material.stock.summary'].search(domain, limit=200)
        
        fields_to_read = [
            'id', 'material_id', 'name', 'mtr_name', 'mtr_type', 'mtr_code', 'rate', 'dimension', 'color_item', 'color_name',
            'supplier','price',
            'qty_opening', 'value_opening', 'qty_in', 'value_in', 'qty_out', 'value_out',
            'qty_closing', 'value_closing','store_id', 'shelf_id', 'shelf_level_id',
        ]
        stock_data = records.read(fields_to_read)
            
        for rec in stock_data:
            rec['store_id'] = rec['store_id'][1] if rec.get('store_id') else ''
            rec['shelf_id'] = rec['shelf_id'][1] if rec.get('shelf_id') else ''
            rec['shelf_level_id'] = rec['shelf_level_id'][1] if rec.get('shelf_level_id') else ''
            rec['mtr_type'] = rec['mtr_type'][1] if rec.get('mtr_type') else ''
            rec['supplier'] = rec['supplier'][1] if rec.get('supplier') else ''
            rec['qty_open'] = rec.pop('qty_opening', 0)
            rec['value_open'] = rec.pop('value_opening', 0)
            rec['qty_close'] = rec.pop('qty_closing', 0)
            rec['value_close'] = rec.pop('value_closing', 0)
            # Ensure value_in and value_out are present
            rec['value_in'] = rec.get('value_in', 0)
            rec['value_out'] = rec.get('value_out', 0)
            
        return stock_data
# endregion
    
    # region Filters Data
    def _get_available_shelves(self, filters):
        domain = []
        if filters.get('filter_store_id'):
            domain.append(('store_id', '=', int(filters['filter_store_id'])))
        return self.env['shelf.list'].search_read(domain, ['id', 'name'])

    def _get_available_shelf_levels(self, filters):
        domain = []
        if filters.get('filter_shelf_id'):
            domain.append(('shelf_id', '=', int(filters['filter_shelf_id'])))
        return self.env['shelf.level'].search_read(domain, ['id', 'name'])
    # endregion

# region Page 2: Program View ('NXT-CT')
    def _get_program_kpis(self, filters):
        order_id = filters.get('filter_order_id')
        total_order_qty = 0
        order_domain = []
        if order_id:
            order_domain.append(('id', '=', int(order_id)))
        
        orders = self.env['warehouse.order'].search(order_domain)
        if orders:
            total_order_qty = sum(orders.mapped('product_code_ids.total_order_qty'))
        return {
            'total_order_qty': total_order_qty,}

    def _get_program_stock_list(self, filters):
        """
        Fetches stock data from 'material.stock.program.summary' for the program view.
        """
        domain = []
        if filters.get('filter_order_id'):
            domain.append(('order_id', '=', int(filters['filter_order_id'])))
                
        records = self.env['material.stock.program.summary'].search(domain, limit=200)
        
        fields_to_read = [
            'id', 'order_id', 'material_id', 'name', 'mtr_code', 'mtr_type', 'rate',
            'dimension', 'color_item','color_name',
            'supplier', 'price', 'qty_opening',
            'value_opening', 'qty_in', 'value_in', 'qty_out', 'value_out',
            'qty_closing', 'value_closing'
        ]
        stock_data = records.read(fields_to_read)
        
        for rec in stock_data:
            rec['order_id'] = rec['order_id'][1] if rec.get('order_id') else ''
            rec['material_id'] = rec['material_id'][1] if rec.get('material_id') else ''
            rec['mtr_type'] = rec['mtr_type'][1] if rec.get('mtr_type') else ''
            rec['supplier'] = rec['supplier'][1] if rec.get('supplier') else ''

            rec['qty_open'] = rec.pop('qty_opening', 0)
            rec['value_open'] = rec.pop('value_opening', 0)
            rec['qty_close'] = rec.pop('qty_closing', 0)
            rec['value_close'] = rec.pop('value_closing', 0)
        return stock_data

# endregion

# region Page 3: XNT Report ('NXT-XNT')
    @api.model
    def get_xnt_report(self, filters):
        """
        Tạo báo cáo Nhập-Xuất-Tồn dựa trên các bộ lọc.
        - Nếu có khoảng thời gian: Tính toán XNT chi tiết.
        - Nếu không có khoảng thời gian: Trả về tồn kho hiện tại.
        
        params = {
            'filter_store_id': int | False,
            'start_date': 'YYYY-MM-DD' | False,
            'end_date': 'YYYY-MM-DD' | False,
        }
        """
        store_id = filters.get('filter_store_id')
        from_date = filters.get('start_date')
        to_date = filters.get('end_date')

        # --- Trường hợp 1: Có chọn khoảng thời gian để xem XNT ---
        if from_date and to_date:
            # 1. Tính tồn đầu kỳ cho tất cả vật tư
            opening_balances = self._compute_opening_balances(store_id, from_date)

            # 2. Tính nhập/xuất trong kỳ cho tất cả vật tư
            period_movements = self._compute_period_movements(store_id, from_date, to_date)

            # 3. Tổng hợp dữ liệu
            all_material_ids = list(set(opening_balances.keys()) | set(period_movements.keys()))
            
            if not all_material_ids:
                return {'lines': [], 'total_materials': 0}

            # Lấy thông tin vật tư trong một lần truy vấn
            materials = self.env['material.item.line'].search([('id', 'in', all_material_ids)])
            material_info_map = {m.id: m for m in materials}

            result_lines = []
            for material_id in all_material_ids:
                opening_qty = opening_balances.get(material_id, 0.0)
                movements = period_movements.get(material_id, (0.0, 0.0))
                qty_in = movements[0] or 0.0
                qty_out = movements[1] or 0.0
                ending_qty = opening_qty + qty_in - qty_out

                # Chỉ hiển thị các dòng có phát sinh hoặc có tồn
                if opening_qty or qty_in or qty_out or ending_qty:
                    material_info = material_info_map.get(material_id)
                    if material_info:
                        result_lines.append({
                            'material_id': material_id,
                            'material_name': material_info.display_name or 'N/A',
                            'material_code': material_info.mtr_code or 'N/A',
                            'mtr_type': material_info.mtr_type.name if material_info.mtr_type else '',
                            'material_unit': material_info.rate or '',
                            'dimension': material_info.dimension or '',
                            'color_item': material_info.color_item or '',
                            'color_name': material_info.color_name or '',
                            'supplier': material_info.supplier.name_supplier if material_info.supplier else '',
                            'price': material_info.price or 0.0,
                            'opening_qty': opening_qty,
                            'value_open': opening_qty * (material_info.price or 0.0),
                            'qty_in': qty_in,
                            'value_in': qty_in * (material_info.price or 0.0),
                            'qty_out': qty_out,
                            'value_out': qty_out * (material_info.price or 0.0),
                            'ending_qty': ending_qty,
                            'value_close': ending_qty * (material_info.price or 0.0),
                        })
            
            return {
                'lines': result_lines,
                'total_materials': len(result_lines),
            }

        # --- Trường hợp 2: Không chọn thời gian, trả về tồn kho hiện tại ---
        else:
            domain = []
            if store_id:
                domain.append(('store_id', '=', int(store_id)))
            
            summary_records = self.env['material.stock.summary'].search(domain)
            
            result_lines = []
            for rec in summary_records:
                if rec.qty_closing != 0:
                    result_lines.append({
                        'material_id': rec.material_id.id,
                        'material_name': rec.material_id.display_name,
                        'material_code': rec.material_id.mtr_code,
                        'mtr_type': rec.material_id.mtr_type.name if rec.material_id.mtr_type else '',
                        'material_unit': rec.material_id.rate,
                        'dimension': rec.material_id.dimension,
                        'color_item': rec.material_id.color_item,
                        'color_name': rec.material_id.color_name,
                        'supplier': rec.material_id.supplier.name_supplier if rec.material_id.supplier else '',
                        'price': rec.material_id.price,
                        'opening_qty': 0,
                        'value_open': 0.0,
                        'qty_in': 0,
                        'value_in': 0.0,
                        'qty_out': 0,
                        'value_out': 0.0,
                        'ending_qty': rec.qty_closing,
                        'value_close': rec.qty_closing * rec.material_id.price,
                    })
            
            return {
                'lines': result_lines,
                'total_materials': len(result_lines),
            }

    def _compute_opening_balances(self, store_id, from_date):
        """Tính tồn đầu kỳ cho tất cả vật tư trước ngày `from_date`."""
        domain = [('date_create', '<', from_date)]
        if store_id:
            domain.append(('store_id', '=', int(store_id)))
        
        grouped_data = self.env['material.stock.card'].read_group(
            domain=domain,
            fields=['qty_in', 'qty_out'],
            groupby=['material_id']
        )
        
        opening_balances = {}
        for group in grouped_data:
            material_id = group['material_id'][0]
            opening_balances[material_id] = group.get('qty_in', 0) - group.get('qty_out', 0)
            
        return opening_balances

    def _compute_period_movements(self, store_id, from_date, to_date):
        """Tính tổng nhập và xuất trong khoảng thời gian cho tất cả vật tư."""
        domain = [
            ('date_create', '>=', from_date),
            ('date_create', '<=', f'{to_date} 23:59:59')  # Bao gồm cả ngày kết thúc
        ]
        if store_id:
            domain.append(('store_id', '=', int(store_id)))
            
        grouped_data = self.env['material.stock.card'].read_group(
            domain=domain,
            fields=['qty_in', 'qty_out'],
            groupby=['material_id']
        )
        
        period_movements = {}
        for group in grouped_data:
            material_id = group['material_id'][0]
            period_movements[material_id] = (group.get('qty_in', 0), group.get('qty_out', 0))
            
        return period_movements

# endregion