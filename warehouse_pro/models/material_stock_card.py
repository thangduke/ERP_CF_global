from odoo import models, fields, api
from odoo.exceptions import ValidationError

class MaterialStockCard(models.Model):
    _name = "material.stock.card"
    _description = "Thẻ kho - Nhập Xuất Tồn"

    material_id = fields.Many2one("material.item.line", string="Dòng Vật tư")
    order_id = fields.Many2one('warehouse.order', string="Chương trình",  store=True, domain="[('state_order','=','validate')]",
                               help="Chọn chương trình liên quan đến phiếu nhập kho.") 
    # Khách hàng liên kết
    customer_id = fields.Many2one('customer.cf', string="Khách hàng", store=True,)
    # --- kho ---
    store_id = fields.Many2one('store.list', string="Kho chứa",required=True )
    shelf_id = fields.Many2one('shelf.list', string="Kệ chứa", )
    shelf_level_id = fields.Many2one('shelf.level', string="Khoang chứa",)
    
    # --- Loại nghiệp vụ ---
    movement_type = fields.Selection([
        ('in', 'Nhập'),
        ('out', 'Xuất'),
        ('adjust', 'Điều chỉnh'),
        ('opening', 'Tồn đầu kỳ')
    ], required=True)
    
    # --- Phiếu nhập, xuất, điều chỉnh ---
    receive_id = fields.Many2one('material.receive', string="Phiếu nhập", store=True,
                                 help="Chọn phiếu nhập kho liên quan đến vật tư này.")
    delivery_id = fields.Many2one('material.delivery', string="Phiếu xuất", store=True,
                                 help="Chọn phiếu xuất kho liên quan đến vật tư này.")
    adjust_id = fields.Many2one('stock.quantity.adjustment', string="Phiếu điều chỉnh", store=True,
                                 help="Chọn phiếu điều chỉnh tồn kho liên quan đến vật tư này.")
    # --- SL, thành tiền ---
    qty_opening = fields.Float("SL tồn đầu")
    value_opening = fields.Float("Dư đầu")
    
    qty_in = fields.Float("SL nhập")
    value_in = fields.Float("Tiền nhập")
    
    qty_out = fields.Float("SL xuất")
    value_out = fields.Float("Tiền xuất")
    
    qty_closing = fields.Float("SL tồn cuối", compute="_compute_stock_total")
    value_closing = fields.Float("Dư cuối", compute="_compute_stock_total")
    
    # --- ngày chứng từ
    date_create = fields.Datetime(string="Ngày chứng từ", default=fields.Datetime.now, readonly=True)
    
    note = fields.Char(string="Ghi chú")
    

    @api.depends("qty_opening", "qty_in", "qty_out",
                 "value_opening", "value_in", "value_out")
    def _compute_stock_total(self):
        for rec in self:
            rec.qty_closing = rec.qty_opening + rec.qty_in - rec.qty_out
            rec.value_closing = rec.value_opening + rec.value_in - rec.value_out

