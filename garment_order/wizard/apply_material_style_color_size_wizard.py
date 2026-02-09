from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta
import logging
from markupsafe import Markup
import json

_logger = logging.getLogger(__name__)


class ApplyMaterialStyleColorSizeWizard(models.TransientModel):
    _name = 'apply.material.style.color.size.wizard'
    _description = 'Áp dụng vật tư từ Style, Size và Màu khác'

    # ==== THÔNG TIN CHÍNH ====
    product_code_id = fields.Many2one(
        'product.code',
        string='Style',
        domain="[('warehouse_order_id', '=', warehouse_order_id)]",
        required=True,
        ondelete='cascade'
    )

    product_color_size_ids = fields.Many2many(
        'product.color.size',
        'apply_wizard_pcs_rel', 'wizard_id', 'pcs_id',
        string="Các style Style cần áp dụng",
        domain="[('product_code_id', '=', product_code_id)]",
        required=True,
        ondelete='cascade'
    )

    customer_id = fields.Many2one(
        'customer.cf',
        string="Khách hàng",
        related='product_code_id.customer_id',
        store=True
    )

    warehouse_order_id = fields.Many2one(
        'warehouse.order',
        string="Chương trình",
        store=True
    )

    line_ids = fields.One2many(
        'apply.material.matrix.line',
        'wizard_id',
        string='Danh sách vật tư'
    )

    # ==== HTML XEM TRƯỚC MA TRẬN ====
    html_preview = fields.Html(
        string="Bảng ma trận",
        compute='_compute_html_preview',
        sanitize=False,
        store=False,
    )

    # ------------------------------------------------------------
    # 🧩 HÀM RENDER MA TRẬN HTML
    # ------------------------------------------------------------
    def _render_color_matrix_html(self, custom_lines=None):
        """
        Sinh HTML cho ma trận vật tư.
        - custom_lines: list of dicts, được ưu tiên sử dụng nếu tồn tại.
        - Nếu không, chuyển đổi self.line_ids (recordset) thành list of dicts.
        - Mã hóa trạng thái hiện tại vào data-lines để client sử dụng.
        """
        self.ensure_one()

        lines_data = []
        if custom_lines is not None:
            lines_data = custom_lines
        elif self.line_ids:
            # Chuyển đổi recordset thành list of dicts để có cấu trúc dữ liệu đồng nhất
            for line in self.line_ids:
                # Xử lý trường hợp line.id là NewId (bản ghi chưa được lưu), không thể JSON hóa
                line_id = line.id if isinstance(line.id, int) else str(line.id)
                lines_data.append({
                    'id': line_id,
                    'program_customer_id': line.program_customer_id.id,
                    'size_ids': line.size_ids.ids,
                    'color_map': line.color_map or {},
                })
        
        lines = lines_data
        material_count = len(lines)

        html_template = """
        <style>
            .matrix-wrapper {{ width: 100%; max-height: 550px; overflow-x: auto;overflow-y: auto; padding: 10px;
                               border: 1px solid #dee2e6;border-radius: 6px;background: #fff;position: relative;}}
            .material-count {{ font-size: 14px; font-weight: bold; color: #333; margin-bottom: 10px; padding-left: 5px; }}
            table.matrix-table {{ width: 100%; border-collapse: collapse; border: 1px solid #dee2e6; min-width: 800px; text-align: center; font-family: 'Segoe UI', sans-serif; font-size: 13px; }}
            table.matrix-table th {{ background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 8px; position: sticky; top: 0; z-index: 10; box-shadow: 0 2px 2px rgba(0,0,0,0.05);}}
            table.matrix-table td {{ border: 1px solid #dee2e6; padding: 6px 8px; white-space: nowrap; text-overflow: ellipsis;overflow: hidden; max-width: 250px; }}
            table.matrix-table td[title] {{ cursor: help; }}
            table.matrix-table td.color-cell, table.matrix-table td.size-cell {{ cursor: pointer; transition: background-color 0.2s ease; }}
            table.matrix-table td.color-cell:hover, table.matrix-table td.size-cell:hover {{ background-color: #f0f8ff; }}
            .empty-text {{ color: #888; text-align: center; padding: 12px; font-style: italic; }}
        </style>
        <div class="matrix-wrapper" data-lines='{lines_json}'>
            <div class="material-count">Tổng số vật tư: {material_count}</div>
            {content}
        </div>
        """

        if not self.product_color_size_ids:
            content = "<div class='alert alert-info'>Vui lòng chọn các style (Color/Size). Ma trận vật tư sẽ tự động hiển thị.</div>"
            return Markup(html_template.format(content=content, lines_json='[]', material_count=0))

        size_ids = self.product_color_size_ids.mapped('size_id')
        color_ids = self.product_color_size_ids.mapped('color_id')

        if not lines:
            content = "<div class='empty-text'>Chưa có dữ liệu vật tư. Ma trận sẽ tự động tải.</div>"
            return Markup(html_template.format(content=content, lines_json='[]', material_count=material_count))

        table_html = "<table class='matrix-table'><thead><tr><th>Mtr#</th><th>Mtr Type</th><th>Mtr Code</th><th>Mtr Name</th><th>Rate</th><th>Supplier</th><th>Dimension</th>"
        for s in size_ids:
            table_html += f"""
                <th class='size-header-cell'>
                    {s.name}<br/>
                    <span class='size-toggle-all' data-size-id='{s.id}' data-select='1' style='cursor: pointer; font-size: 1.1em;' title='Chọn tất cả'>✅</span>
                    <span class='size-toggle-all' data-size-id='{s.id}' data-select='0' style='cursor: pointer; font-size: 1.1em;' title='Bỏ chọn tất cả'>⬜</span>
                </th>"""
        for c in color_ids:
            table_html += f"""
                <th class='color-header-cell'>
                    {c.name}<br/>
                    <a href='#' class='color-toggle-all-apply' data-style-color-id='{c.id}' title='Áp dụng cho tất cả' style='text-decoration: none; font-size: 1.1em;'>🎨</a>
                    <a href='#' class='color-toggle-all-clear' data-style-color-id='{c.id}' title='Bỏ chọn tất cả' style='text-decoration: none; font-size: 1.1em; margin-left: 4px;'>🗑️</a>
                </th>"""
        table_html += "</tr></thead><tbody>"

        # Tải trước dữ liệu để tối ưu
        program_customer_ids = [line['program_customer_id'] for line in lines]
        base_materials = self.env['program.customer'].browse(program_customer_ids).read(['mtr_no', 'mtr_type', 'mtr_code', 'mtr_name', 'rate', 'supplier', 'dimension'])
        base_materials_map = {mat['id']: mat for mat in base_materials}
        
        material_color_ids = []
        for line in lines:
            color_map = line.get('color_map', {})
            if isinstance(color_map, dict):
                material_color_ids.extend(color_map.values())

        material_colors = self.env['material.color'].browse(list(set(material_color_ids))).read(['color_name'])
        material_colors_map = {mc['id']: mc for mc in material_colors}

        for line in lines:
            program_customer_id = line['program_customer_id']
            base_material = base_materials_map.get(program_customer_id)
            if not base_material:
                continue

            supplier_name = base_material.get('supplier')[1] if base_material.get('supplier') else ''
            mtr_type_name = base_material.get('mtr_type')[1] if base_material.get('mtr_type') else ''

            table_html += "<tr>"
            table_html += f"<td title='{base_material.get('mtr_no', '')}'>{base_material.get('mtr_no', '')}</td>"
            table_html += f"<td title='{mtr_type_name}'>{mtr_type_name}</td>"
            table_html += f"<td title='{base_material.get('mtr_code', '')}'>{base_material.get('mtr_code', '')}</td>"
            table_html += f"<td title='{base_material.get('mtr_name', '')}'>{base_material.get('mtr_name', '')}</td>"
            table_html += f"<td>{base_material.get('rate', '')}</td>"
            table_html += f"<td title='{supplier_name}'>{supplier_name}</td>"
            table_html += f"<td title='{base_material.get('dimension', '')}'>{base_material.get('dimension', '')}</td>"
            
            line_size_ids = line.get('size_ids', [])
            for s in size_ids:
                is_checked = s.id in line_size_ids
                checked = '✅' if is_checked else '⬜'
                table_html += (
                    f"<td class='size-cell text-center' "
                    f"data-program-customer-id='{program_customer_id}' "
                    f"data-size-id='{s.id}' data-is-checked='{1 if is_checked else 0}' style='font-size: 1.2em;'>{checked}</td>"
                )

            color_map_dict = line.get('color_map', {})
            for c in color_ids:
                material_color_id = color_map_dict.get(str(c.id))
                color_name = ''
                if material_color_id:
                    material_color = material_colors_map.get(material_color_id)
                    if material_color:
                        color_name = material_color.get('color_name', '')
                table_html += (
                    f"<td class='color-cell' "
                    f"data-program-customer-id='{program_customer_id}' "
                    f"data-style-color-id='{c.id}'>{color_name or '-'}</td>"
                )
            table_html += "</tr>"

        table_html += "</tbody></table>"
        
        # Mã hóa trạng thái mới nhất của các dòng vào JSON
        json_lines = json.dumps(lines)
        
        return Markup(html_template.format(content=table_html, lines_json=json_lines, material_count=material_count))

    @api.depends('line_ids', 'product_color_size_ids', 'line_ids.size_ids', 'line_ids.color_map')
    def _compute_html_preview(self):
        for wiz in self:
            wiz.html_preview = wiz._render_color_matrix_html()

    def _get_line_creation_commands(self):
        """
        Tạo các dòng ma trận dựa trên product.color.size đã chọn.
        Mỗi dòng vật tư được xác định theo tổ hợp:
            - program_customer_line_id
            - dimension
            - supplier
            - material_color_id (nếu có)
        """
        self.ensure_one()
        if not self.product_color_size_ids:
            return [(5, 0, 0)]

        lines_to_create = []
        aggregated = {}

        for pcs in self.product_color_size_ids:
            style_color_id = pcs.color_id.id
            style_color_str = str(style_color_id)
            size_id = pcs.size_id.id

            for material in pcs.material_ids:
                # tổ hợp tìm vật tư đại diện chính xác
                domain = [
                    ('program_customer_line_id', '=', material.program_customer_line_id.id),
                    ('dimension', '=', material.dimension),
                    ('supplier', '=', material.supplier.id),
                ]
                if material.material_color_id:
                    domain.append(('material_color_id', '=', material.material_color_id.id))
                else:
                    domain.append(('material_color_id', '=', False))

                rep_material = self.env['program.customer'].search(domain, limit=1)
                if not rep_material:
                    continue

                # tạo key duy nhất cho từng vật tư theo tổ hợp
                rep_key = (
                    f"{rep_material.program_customer_line_id.id}-"
                    f"{rep_material.dimension}-"
                    f"{rep_material.supplier.id}-"
                    f"{rep_material.material_color_id.id if rep_material.material_color_id else 0}"
                )

                if rep_key not in aggregated:
                    aggregated[rep_key] = {
                        'program_customer_id': rep_material.id,
                        'size_ids': set(),
                        'color_map': {},
                    }

                aggregated[rep_key]['size_ids'].add(size_id)

                if material.material_color_id:
                    aggregated[rep_key]['color_map'][style_color_str] = material.material_color_id.id

        # convert sang command
        for key, vals in aggregated.items():
            lines_to_create.append({
                'program_customer_id': vals['program_customer_id'],
                'size_ids': [(6, 0, list(vals['size_ids']))],
                'color_map': vals['color_map'],
            })

        return [(5, 0, 0)] + [(0, 0, line) for line in lines_to_create]

    
    @api.onchange('product_color_size_ids')
    def _onchange_load_materials(self):
        """Sử dụng hàm helper để gán dữ liệu trong onchange."""
        self.line_ids = self._get_line_creation_commands()
        
    @api.model
    def update_color_map(self, wizard_id, current_lines, program_customer_id, style_color_id, material_color_id):
        """
        Cập nhật color_map trong bộ nhớ (danh sách dicts) và render lại HTML.
        Không dựa vào trạng thái của wizard record.
        """
        wizard = self.browse(wizard_id)
        if not wizard.exists():
            raise UserError(f"Không tìm thấy wizard (ID: {wizard_id}).")

        # Đảm bảo current_lines là một list of dicts
        if isinstance(current_lines, str):
            current_lines = json.loads(current_lines)

        target_line = None
        for line in current_lines:
            if line['program_customer_id'] == int(program_customer_id):
                target_line = line
                break
        
        if not target_line:
            # Điều này không nên xảy ra nếu client gửi dữ liệu đúng
            raise UserError(f"Không tìm thấy dòng vật tư (ID: {program_customer_id}) trong dữ liệu hiện tại.")

        color_map = target_line.get('color_map', {})
        if material_color_id:
            color_map[str(int(style_color_id))] = int(material_color_id)
        else:
            color_map.pop(str(int(style_color_id)), None)
        target_line['color_map'] = color_map
        
        return wizard._render_color_matrix_html(custom_lines=current_lines)

    @api.model
    def update_size_selection(self, wizard_id, current_lines, program_customer_id, size_id, is_selected):
        """
        Cập nhật size trong bộ nhớ (danh sách dicts) và render lại HTML.
        Không dựa vào trạng thái của wizard record.
        """
        wizard = self.browse(wizard_id)
        if not wizard.exists():
            raise UserError(f"Không tìm thấy wizard (ID: {wizard_id}).")

        # Đảm bảo current_lines là một list of dicts
        if isinstance(current_lines, str):
            current_lines = json.loads(current_lines)

        target_line = None
        for line in current_lines:
            if line['program_customer_id'] == int(program_customer_id):
                target_line = line
                break

        if not target_line:
            # Điều này không nên xảy ra nếu client gửi dữ liệu đúng
            raise UserError(f"Không tìm thấy dòng vật tư (ID: {program_customer_id}) trong dữ liệu hiện tại.")

        line_size_ids = set(target_line.get('size_ids', []))
        size_id = int(size_id)
        if is_selected:
            line_size_ids.add(size_id)
        else:
            line_size_ids.discard(size_id)
        target_line['size_ids'] = list(line_size_ids)
        
        return wizard._render_color_matrix_html(custom_lines=current_lines)

    @api.model
    def toggle_all_sizes_for_column(self, wizard_id, current_lines, size_id, is_selected):
        """
        Chọn hoặc bỏ chọn tất cả vật tư cho một cột size cụ thể.
        """
        wizard = self.browse(wizard_id)
        if not wizard.exists():
            raise UserError(f"Không tìm thấy wizard (ID: {wizard_id}).")

        if isinstance(current_lines, str):
            current_lines = json.loads(current_lines)

        size_id = int(size_id)
        is_selected = bool(int(is_selected))

        for line in current_lines:
            line_size_ids = set(line.get('size_ids', []))
            if is_selected:
                line_size_ids.add(size_id)
            else:
                line_size_ids.discard(size_id)
            line['size_ids'] = list(line_size_ids)
        
        return wizard._render_color_matrix_html(custom_lines=current_lines)
    
    @api.model
    def clear_all_colors_for_column(self, wizard_id, current_lines, style_color_id):
        """
        Xóa tất cả các màu vật tư cho một cột màu (style.color) cụ thể.
        """
        wizard = self.browse(wizard_id)
        if not wizard.exists():
            raise UserError(f"Không tìm thấy wizard (ID: {wizard_id}).")

        if isinstance(current_lines, str):
            current_lines = json.loads(current_lines)

        style_color_id_str = str(int(style_color_id))

        for line in current_lines:
            color_map = line.get('color_map', {})
            if style_color_id_str in color_map:
                color_map.pop(style_color_id_str)
            line['color_map'] = color_map
        
        return wizard._render_color_matrix_html(custom_lines=current_lines)

    @api.model
    def auto_apply_color_for_column(self, wizard_id, current_lines, style_color_id):
        """
        Tự động áp dụng màu vật tư đầu tiên tìm thấy cho tất cả các dòng trong một cột.
        For each line, it finds the corresponding program.customer.line, then finds the first
        associated program.customer record that has a material_color_id, and applies that color.
        """
        wizard = self.browse(wizard_id)
        if not wizard.exists():
            raise UserError(f"Không tìm thấy wizard (ID: {wizard_id}).")

        if isinstance(current_lines, str):
            current_lines = json.loads(current_lines)

        style_color_id_str = str(int(style_color_id))
        
        program_customer_ids = [line['program_customer_id'] for line in current_lines]
        rep_materials = self.env['program.customer'].browse(program_customer_ids)
        
        rep_material_map = {mat.id: mat.program_customer_line_id.id for mat in rep_materials}
        program_customer_line_ids = list(set(rep_material_map.values()))

        related_materials_with_color = self.env['program.customer'].search([
            ('program_customer_line_id', 'in', program_customer_line_ids),
            ('material_color_id', '!=', False)
        ])

        color_cache = {}
        for mat in related_materials_with_color:
            line_id = mat.program_customer_line_id.id
            if line_id not in color_cache:
                color_cache[line_id] = mat.material_color_id.id

        for line in current_lines:
            rep_material_id = line['program_customer_id']
            program_customer_line_id = rep_material_map.get(rep_material_id)
            
            if program_customer_line_id:
                material_color_id = color_cache.get(program_customer_line_id)
                if material_color_id:
                    color_map = line.get('color_map', {})
                    color_map[style_color_id_str] = material_color_id
                    line['color_map'] = color_map
        
        return wizard._render_color_matrix_html(custom_lines=current_lines)
    
    @api.model
    def sync_lines_before_action(self, wizard_id, full_lines_json):
        """
        Đồng bộ hóa toàn bộ trạng thái của ma trận từ client lên server.
        Phương thức này sẽ xóa tất cả các dòng hiện có và tạo lại chúng từ JSON
        được gửi từ client, đảm bảo self.line_ids luôn cập nhật trước khi
        chạy action_apply.
        """
        wiz = self.browse(wizard_id)
        if not wiz.exists():
            _logger.warning("sync_lines_before_action: không tìm thấy wizard ID %s", wizard_id)
            return False

        # Xóa tất cả các dòng cũ để đảm bảo không có dữ liệu rác
        wiz.write({'line_ids': [(5, 0, 0)]})

        try:
            lines = json.loads(full_lines_json)
        except (json.JSONDecodeError, TypeError):
            _logger.error("Lỗi giải mã JSON trong sync_lines_before_action: %s", full_lines_json)
            raise UserError("Dữ liệu gửi từ client không hợp lệ.")

        commands = []
        for line in lines:
            program_customer_id = line.get('program_customer_id')
            if not program_customer_id:
                continue
            
            # Quan trọng: Gán dictionary trực tiếp cho trường Json.
            # Odoo sẽ tự động mã hóa nó thành chuỗi JSON trong DB.
            # KHÔNG dùng json.dumps() ở đây.
            create_vals = {
                'program_customer_id': program_customer_id,
                'size_ids': [(6, 0, line.get('size_ids', []))],
                'color_map': line.get('color_map', {}),
            }
            commands.append((0, 0, create_vals))

        if commands:
            wiz.write({'line_ids': commands})
        
        _logger.info("✅ Đồng bộ hóa thành công %s dòng cho wizard %s", len(commands), wizard_id)
        return True
    
    
    def action_apply(self):
        """
        Lưu các thay đổi từ wizard vào các bản ghi product.color.size.
        Phương thức này đảm bảo đồng bộ hóa chính xác giữa bảng vật tư của wizard
        và các vật tư được liên kết với mỗi style.
        - Thêm vật tư nếu chúng được chọn.
        - Xóa vật tư nếu chúng bị bỏ chọn.
        - Tạo các biến thể vật tư mới (program.customer) nếu cần.
        """
        self.ensure_one()
        _logger.info("🚀 Bắt đầu action_apply cho wizard %s", self.id)

        if not self.line_ids:
            _logger.warning("action_apply: self.line_ids trống. Tiến hành xóa tất cả vật tư khỏi các style đã chọn.")

        warehouse_order = self.product_code_id.warehouse_order_id
        if not warehouse_order:
            _logger.warning("🔥 action_apply bị hủy vì không tìm thấy warehouse_order.")
            return

        ProgramCustomer = self.env['program.customer']

        # 1. Cache tất cả các bản ghi vật tư hiện có cho chương trình này để tránh truy vấn DB lặp lại.
        # Khóa phải là duy nhất cho mỗi biến thể vật tư, bao gồm cả dimension.
        all_program_instances = ProgramCustomer.search([('warehouse_order_ids', '=', warehouse_order.id)])
        instance_cache = {
            (inst.program_customer_line_id.id, inst.material_color_id.id, inst.supplier.id, inst.dimension): inst
            for inst in all_program_instances
        }

        # 2. Lặp qua từng style (product.color.size) cần được cập nhật.
        for pcs_variant in self.product_color_size_ids:
            materials_to_link = []

            # 3. Đối với mỗi style, lặp qua các hàng trong ma trận để tìm các vật tư áp dụng.
            for line in self.line_ids:
                # Kiểm tra xem size của style có được chọn cho hàng vật tư này không.
                if pcs_variant.size_id.id not in line.size_ids.ids:
                    continue

                # Kiểm tra xem có màu vật tư được ánh xạ cho màu của style không.
                style_color_id_str = str(pcs_variant.color_id.id)
                
                color_map = line.color_map
                if isinstance(color_map, str):
                    try:
                        color_map = json.loads(color_map)
                    except (json.JSONDecodeError, TypeError):
                        color_map = {}

                material_color_id = color_map.get(style_color_id_str)

                if not material_color_id:
                    continue

                # 4. Một vật tư được chọn. Tìm hoặc tạo bản ghi program.customer tương ứng.
                base_material = line.program_customer_id
                
                # Khóa phải bao gồm tất cả các thuộc tính duy nhất: line_id, color, supplier và dimension.
                instance_key = (
                    base_material.program_customer_line_id.id,
                    int(material_color_id),
                    base_material.supplier.id,
                    base_material.dimension
                )
                
                program_customer_instance = instance_cache.get(instance_key)

                if not program_customer_instance:
                    # Nếu chưa tồn tại, hãy tạo nó và thêm vào cache.
                    _logger.info("...Tạo mới program.customer cho khóa: %s", instance_key)
                    create_vals = {
                        'program_customer_line_id': instance_key[0],
                        'material_color_id': instance_key[1],
                        'supplier': instance_key[2],
                        'dimension': instance_key[3],
                        'warehouse_order_ids': [(4, warehouse_order.id)],
                        'mtr_code': base_material.mtr_code,
                        'mtr_name': base_material.mtr_name,
                        'mtr_type': base_material.mtr_type.id,
                        'rate': base_material.rate,
                    }
                    program_customer_instance = ProgramCustomer.create(create_vals)
                    instance_cache[instance_key] = program_customer_instance
                
                materials_to_link.append(program_customer_instance.id)

            # 5. Cập nhật product.color.size với danh sách vật tư đã được đồng bộ hóa.
            _logger.info("...Style '%s': liên kết với %s vật tư.", pcs_variant.display_name, len(materials_to_link))
            pcs_variant.write({'material_ids': [(6, 0, materials_to_link)]})

        _logger.info("✅ Hoàn tất action_apply cho wizard %s.", self.id)
        message = "✅ Đã đồng bộ hóa vật tư thành công cho các style đã chọn."
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': message,
                'sticky': False,
                'type': 'success'
            }
        }
    
class ApplyMaterialMatrixLine(models.TransientModel):
    _name = 'apply.material.matrix.line'
    _description = 'Dòng Ma Trận Vật Tư (Wizard)'

    wizard_id = fields.Many2one('apply.material.style.color.size.wizard', string='Wizard', ondelete='cascade', index=True)
    program_customer_id = fields.Many2one('program.customer', string='Dòng vật tư', required=True, ondelete='cascade')
    size_ids = fields.Many2many('product.size', 'apply_wizard_line_size_rel', 'line_id', 'size_id', string='Sizes')
    color_map = fields.Json(string='Bản đồ màu (color_id: material_color_id)')