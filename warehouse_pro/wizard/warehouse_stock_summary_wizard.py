from odoo import models, fields, api

class WarehouseStockSummaryWizard(models.TransientModel):
    _name = 'warehouse.stock.summary.wizard'
    _description = 'Wizard tổng hợp vật tư đã gộp của tất cả các kho'

    summary_line_ids = fields.One2many(
        'warehouse.stock.summary', 'wizard_id', string='Vật tư đã gộp', compute='_compute_summary_lines', store=False
    )

    @api.depends()
    def _compute_summary_lines(self):
        for wizard in self:
         #   self.env['warehouse.stock.summary'].search([('wizard_id', '=', wizard.id)]).unlink()
            group_dict = {}
            all_lines = self.env['shelf.material.line'].search([])
            for line in all_lines:
                key = (
                    line.mtr_no,
                    line.mtr_type.id if line.mtr_type else False,
                    line.mtr_code,
                    line.mtr_name,
                    line.dimension,
                    line.color_item,
                    line.color_name,
                    line.color_set,
                    line.color_code,
                )
                if key not in group_dict:
                    group_dict[key] = {
                        'wizard_id': wizard.id,
                        'mtr_no': line.mtr_no,
                        'mtr_type': line.mtr_type.id if line.mtr_type else False,
                        'mtr_code': line.mtr_code,
                        'mtr_name': line.mtr_name,
                        'dimension': line.dimension,
                        'color_item': line.color_item,
                        'color_name': line.color_name,
                        'color_set': line.color_set,
                        'color_code': line.color_code,
                        'est_qty': 0,
                        'act_qty': 0,
                        'rate': line.rate,
                        'supplier': line.supplier,
                        'country': line.country,
                    }
                group_dict[key]['est_qty'] += line.est_qty or 0
                group_dict[key]['act_qty'] += line.act_qty or 0
            for vals in group_dict.values():
                self.env['warehouse.stock.summary'].create(vals)
            wizard.summary_line_ids = self.env['warehouse.stock.summary'].search([('wizard_id', '=', wizard.id)])
            
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
    
    def action_export(self):
        """Export danh sách vật tư trong đơn nhập kho"""
        self.ensure_one()
        return {}
    
class WarehouseStockSummary(models.TransientModel):
    _name = 'warehouse.stock.summary'
    _description = 'Vật tư đã gộp của tất cả các kho (tạm thời)'

    wizard_id = fields.Many2one('warehouse.stock.summary.wizard', string='Wizard', ondelete='cascade')
    position = fields.Char(string="Vị trí sử dụng", help="Số thứ tự vị trí") 
    mtr_no = fields.Char(string='Mã vật tư')
    mtr_type = fields.Many2one('material.type', string="Type")
    mtr_code = fields.Char(string='Code item của nhà cung cấp')
    mtr_name = fields.Char(string='Tên vật tư')
    dimension = fields.Char(string='Kích thước')
    color_item = fields.Char(string='Mã màu vật tư')
    color_name = fields.Char(string='Tên màu')
    color_set = fields.Char(string='Color Set')
    color_code = fields.Char(string='Color Code')
    est_qty = fields.Float(string='SL ước tính')
    act_qty = fields.Float(string='SL thực tế')
    rate = fields.Char(string='Đơn vị tính')
    supplier = fields.Char(string="Nhà cung cấp")
    country = fields.Char(string="Quốc gia")
