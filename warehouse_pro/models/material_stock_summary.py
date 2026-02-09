from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re

class MaterialStockSummary(models.Model):
    _name = 'material.stock.summary'
    _description = 'Tổng hợp vật tư tồn kho'
    _rec_name = 'name'
    _order = 'mtr_no_sort_key asc'

    # Display Name
    display_name = fields.Char(string="Display Name", compute='_compute_display_name', store=False)

    # Core Fields
    material_id = fields.Many2one('material.item.line', string="Vật tư", required=True, ondelete='cascade')
    store_id = fields.Many2one('store.list', string="Kho chứa", ondelete='cascade')
    shelf_id = fields.Many2one('shelf.list', string="Kệ chứa")
    shelf_level_id = fields.Many2one('shelf.level', string="Khoang chứa")
    
    name = fields.Char(related='material_id.name', string="Mtr#")
    # Material Info (Related)
    position = fields.Char(related='material_id.position', string="Position")
    mtr_no = fields.Char(related='material_id.mtr_no', string='Mtr_no')
    mtr_no_sort_key = fields.Integer(related='material_id.mtr_no_sort_key', string="Sort Key")
    
    mtr_type = fields.Many2one('material.type',string="Mtr_type", related='material_id.mtr_type', store=False)
    mtr_name = fields.Char(related='material_id.mtr_name', string='Mtr_name')
    mtr_code = fields.Char(related='material_id.mtr_code', string='Mtr_code')
    rate = fields.Char(related='material_id.rate', string="Unit")
    
    dimension = fields.Char(related='material_id.dimension', string='Dimension')
    
    color_item = fields.Char(string="Color#", related='material_id.color_item', help="Mã item màu",)
    color_code = fields.Char(string="Color Code", related='material_id.color_code', help="Mã code màu")
    color_name = fields.Char(string="Color Name", related='material_id.color_name', help="Tên màu")
    color_set = fields.Char(string="Color Set", related='material_id.color_set', help="Bộ màu")

    supplier = fields.Many2one(related='material_id.supplier', string="Supplier")
    country = fields.Char(related='material_id.country', string="Country")

    # Transactional Fields
    price = fields.Float(string="Price", related='material_id.price', digits=(16, 3),)
    cif_price = fields.Float(string="CIF.Price", related='material_id.cif_price', digits=(16, 3), help="Giá bán cho khách hàng")
    fob_price = fields.Float(string="FOB.Price", related='material_id.fob_price', digits=(16, 3), help="Giá mua vào")
    exwork_price = fields.Float(string="EXW.Price", related='material_id.exwork_price', digits=(16, 3), help="Giá xuất xưởng")

    qty_opening = fields.Float("SL tồn đầu")
    value_opening = fields.Float("Dư đầu")
    
    qty_in = fields.Float("SL nhập")
    value_in = fields.Float("Tiền nhập")
    
    qty_out = fields.Float("SL xuất")
    value_out = fields.Float("Tiền xuất")
    
    qty_closing = fields.Float("SL tồn cuối", compute="_compute_stock_total")
    value_closing = fields.Float("Dư cuối", compute="_compute_stock_total")

    @api.depends("qty_opening", "qty_in", "qty_out", "value_opening", "value_in", "value_out")
    def _compute_stock_total(self):
        for rec in self:
            rec.qty_closing = rec.qty_opening + rec.qty_in - rec.qty_out
            rec.value_closing = rec.value_opening + rec.value_in - rec.value_out
            
    is_selected = fields.Boolean(string="Chọn", default=False) 
            
            
            
class MaterialStockProgramSummary(models.Model):
    _name = 'material.stock.program.summary'
    _description = 'Tổng hợp vật tư tồn kho theo chương trình '
    _rec_name = 'name'
    _order = 'mtr_no_sort_key asc'
    
    # Display Name
    display_name = fields.Char(string="Display Name", compute='_compute_display_name', store=False)

    # Core Fields
    material_id = fields.Many2one('material.item.line', string="Vật tư", required=True, ondelete='cascade')

    order_id = fields.Many2one('warehouse.order', string="Chương trình",  store=True,
                               help="Chọn chương trình liên quan đến phiếu nhập kho.")
    
    name = fields.Char(related='material_id.name', string="Mtr#")
    # Material Info (Related)
    position = fields.Char(related='material_id.position', string="Position")
    mtr_no = fields.Char(related='material_id.mtr_no', string='Mtr_no')
    mtr_no_sort_key = fields.Integer(related='material_id.mtr_no_sort_key', string="Sort Key")
    mtr_type = fields.Many2one('material.type',string="Mtr_type", related='material_id.mtr_type', store=False)
    mtr_name = fields.Char(related='material_id.mtr_name', string='Mtr_name')
    mtr_code = fields.Char(related='material_id.mtr_code', string='Mtr_code')
    rate = fields.Char(related='material_id.rate', string="Unit")
    
    dimension = fields.Char(related='material_id.dimension', string='Dimension')
    
    color_item = fields.Char(string="Color#", related='material_id.color_item', help="Mã item màu",)
    color_code = fields.Char(string="Color Code", related='material_id.color_code', help="Mã code màu")
    color_name = fields.Char(string="Color Name", related='material_id.color_name', help="Tên màu")
    color_set = fields.Char(string="Color Set", related='material_id.color_set', help="Bộ màu")

    supplier = fields.Many2one('supplier.partner', related='material_id.supplier', string="Supplier", help="Nhà cung cấp",)
    country = fields.Char(related='material_id.country', string="Country")

    # Transactional Fields
    price = fields.Float(string="Price", related='material_id.price', digits=(16, 3),)
    cif_price = fields.Float(string="CIF.Price", related='material_id.cif_price', digits=(16, 3), help="Giá bán cho khách hàng")
    fob_price = fields.Float(string="FOB.Price", related='material_id.fob_price', digits=(16, 3), help="Giá mua vào")
    exwork_price = fields.Float(string="EXW.Price", related='material_id.exwork_price', digits=(16, 3), help="Giá xuất xưởng")

    @api.depends('mtr_no', 'mtr_name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"[{rec.mtr_no or ''}] {rec.mtr_name or ''}"

    qty_opening = fields.Float("SL tồn đầu")
    value_opening = fields.Float("Dư đầu")
    
    qty_in = fields.Float("SL nhập")
    value_in = fields.Float("Tiền nhập")
    
    qty_out = fields.Float("SL xuất")
    value_out = fields.Float("Tiền xuất")
    
    qty_closing = fields.Float("SL tồn cuối", compute="_compute_stock_total")
    value_closing = fields.Float("Dư cuối", compute="_compute_stock_total")

    @api.depends("qty_opening", "qty_in", "qty_out", "value_opening", "value_in", "value_out")
    def _compute_stock_total(self):
        for rec in self:
            rec.qty_closing = rec.qty_opening + rec.qty_in - rec.qty_out
            rec.value_closing = rec.value_opening + rec.value_in - rec.value_out
            