from odoo import models, fields

class StockQuantityAdjustmentLine(models.Model):
    _name = 'stock.quantity.adjustment.line'
    _description = 'Chi tiết điều chỉnh số lượng tồn kho'

    adjustment_id = fields.Many2one(
        'stock.quantity.adjustment',
        string="Yêu cầu điều chỉnh", ondelete="cascade"
    )
    # Thay thế material_line_id bằng stock_summary_id
    stock_summary_id = fields.Many2one('material.stock.summary', string="Dòng tồn kho")
    program_stock_summary_id = fields.Many2one('material.stock.program.summary', string="Dòng tồn kho chương trình")  
    
    name = fields.Char(string="Mtr#", readonly=True)
    position = fields.Char(string="Position", readonly=True)
    # Các trường thông tin vật tư (có thể giữ lại để hiển thị)
    mtr_no = fields.Char(string="Mtr_no", readonly=True)
    mtr_type = fields.Many2one('material.type', string="Mtr_type", readonly=True)
    mtr_code = fields.Char(string="Mtr_code", readonly=True)
    mtr_name = fields.Char(string="Mtr_name", readonly=True)
    dimension = fields.Char(string="Dimension", readonly=True)
    color_item = fields.Char(string="Color#", readonly=True)
    color_name = fields.Char(string="Color_name", readonly=True)
    color_set = fields.Char(string="Color_set", readonly=True)
    rate = fields.Char(string="Rate", readonly=True)
    supplier = fields.Many2one('supplier.partner', string="Supplier", readonly=True)
    country = fields.Char(string="Country", readonly=True)
    
    price = fields.Float(string="Price", readonly=True)
    cif_price = fields.Float(string="CIF.Price", readonly=True)
    fob_price = fields.Float(string="FOB.Price", readonly=True)
    exwork_price = fields.Float(string="EXW.Price", readonly=True)

    qty_before = fields.Float(string="SL trước điều chỉnh", readonly=True)
    qty_change = fields.Float(string="SL sau điều chỉnh")