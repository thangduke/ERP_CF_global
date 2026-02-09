from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)

class MaterialInvoiceCreateWizard(models.TransientModel):
    _name = 'material.invoice.create.wizard'
    _description = 'Tạo phiếu đặt hàng theo từng đợt'

    po_id = fields.Many2one('material.purchase.order', string='PO', required=True , invisible="1")
    line_ids = fields.One2many('material.invoice.create.wizard.line', 'wizard_id', string='Dòng vật tư cần đặt hàng')
    supplier_id = fields.Many2one('supplier.partner', string='Nhà cung cấp')  # <-- Thêm dòng này
    entry_date = fields.Date(string="Ngày đặt hàng", default=fields.Datetime.now, required=True)

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        po = self.env['material.purchase.order'].browse(self._context.get('default_po_id'))
        lines = []

        for po_line in po.line_ids:
            total_received = sum(self.env['material.invoice.line'].search([
                ('po_line_id', '=', po_line.id)
            ]).mapped('act_qty'))
            remaining = po_line.est_qty - total_received
            # 👉 Nếu trạng thái là add_po, luôn hiển thị toàn bộ vật tư
            if remaining > 0:
                lines.append((0, 0, {
                    'material_line_id': po_line.id,
                    'name': po_line.name,
                    'est_qty': po_line.est_qty,
                    'remaining_qty': remaining,
                    'act_qty': remaining,

                }))
        res.update({
            'po_id': po.id,
            'supplier_id': po.supplier_id.id,
            'line_ids': lines,
        })
        return res
  
    def action_confirm(self):
        invoice = self.env['material.invoice'].create({
            'po_id': self.po_id.id,
            'supplier': self.supplier_id.id,
            'order_id': self.po_id.order_id.id,
        })

        for line in self.line_ids:
            po_line = line.material_line_id
            remaining = (po_line.est_qty or 0.0) - (po_line.act_qty or 0.0)

            if line.act_qty > remaining:
                raise UserError(
                    f"Số lượng nhập ({line.act_qty}) vượt quá số lượng còn lại ({line.remaining_qty}) của vật tư '{line.name}'."
                )
            if line.act_qty > 0:
                
                po_line = line.material_line_id
                self.env['material.invoice.line'].create({
                    'invoice_id': invoice.id,
                    'po_line_id': line.material_line_id.id,
                    
                    'name': po_line.name,
                    'position': po_line.position,
                    'mtr_no' : po_line.mtr_no,
                    'mtr_type': po_line.mtr_type.id,
                    'mtr_code': po_line.mtr_code,
                    'mtr_name': po_line.mtr_name,
                    'rate': po_line.rate,              
                    'dimension': po_line.dimension,
                    
                    'color_item': po_line.color_item,
                    'color_code': po_line.color_code,
                    'color_name': po_line.color_name,
                    'color_set': po_line.color_set,
                    
                    'supplier': po_line.supplier.id if po_line.supplier else False,
                    'country': po_line.country,
                    
                    'act_qty': line.act_qty,
                    'inv_qty': line.act_qty,
                    'est_qty': po_line.est_qty,
                    
                    'price': line.material_line_id.price,
                    'cif_price': line.material_line_id.cif_price,
                    'fob_price': line.material_line_id.fob_price,
                    'exwork_price': line.material_line_id.exwork_price,

                })
                # Cập nhật số lượng đã nhập về dòng vật tư gốc
                po_line.act_qty = (po_line.act_qty or 0) + line.act_qty

class MaterialInvoiceCreateWizardLine(models.TransientModel):
    _name = 'material.invoice.create.wizard.line'
    _description = 'Dòng vật tư cần đặt hàng theo wizard'

    wizard_id = fields.Many2one('material.invoice.create.wizard', string='Wizard')
    wizard_po_id = fields.Many2one('request.add.po.wizard', string='Vật tư đặt thêm', )
    material_line_id = fields.Many2one('material.line', string='Dòng vật tư gốc')

    name = fields.Char(string='Mtr#')
    position = fields.Char(string="Position", related='material_line_id.position', help="Vị trí vật tư",readonly="1")
    mtr_no = fields.Char(string='Mtr#', related='material_line_id.mtr_no', help='Mã code vật tư', readonly="1")  # Mã vật tư / Mtr No
    mtr_type = fields.Many2one('material.type', related='material_line_id.mtr_type', string="Mtr Type", help="Loại vật tư", readonly="1")
    mtr_code = fields.Char(string='Mtr Code', related='material_line_id.mtr_code', help='Code item của nhà cung cấp', readonly="1")
    mtr_name = fields.Char(string="Mtr Name", related='material_line_id.mtr_name', help="Tên vật tư", readonly="1")
    rate = fields.Char(string="Unit", related='material_line_id.rate', help='Ví dụ: mét, cuộn, cái...', readonly="1")
    
    # >> Kích thước
    dimension = fields.Char(string='Dimension', related='material_line_id.dimension', help="Kích thước vật tư", readonly="1") 

    # >> Màu sắc
    color_item = fields.Char(string="Color#", related='material_line_id.color_item', help="Mã item màu", readonly="1")
    color_code = fields.Char(string="Color Code", related='material_line_id.color_code', help="Mã code màu", readonly="1")
    color_name = fields.Char(string="Color Name", related='material_line_id.color_name', help="Tên màu", readonly="1")
    color_set = fields.Char(string="Color Set", related='material_line_id.color_set', help="Bộ màu", readonly="1")    

    # >> Thông tin nhà cung cấp
    supplier = fields.Many2one('supplier.partner', related='material_line_id.supplier', string="Supplier", help="Nhà cung cấp", readonly="1")
    country = fields.Char(string="Quốc gia", related='material_line_id.country', help=" Quốc gia nhà cung cấp", readonly="1")
    
    est_qty = fields.Float(string='SL Đặt', digits=(16, 3), help='Số lượng đặt hàng',default=0.0)
    remaining_qty = fields.Float(string='SL Còn lại', digits=(16, 3), help='Số lượng còn lại để đặt hàng',default=0.0)
    act_qty = fields.Float(string='SL Đặt đợt này' , digits=(16, 3), help='Số lượng đặt hàng trong đợt này', default=0.0)

    # Price/FOB Price/EXW Price/
    price = fields.Float(string="Price", related='material_line_id.price', digits=(16, 3),)
    cif_price = fields.Float(string="CIF.Price", related='material_line_id.cif_price', digits=(16, 3), help="Giá bán cho khách hàng")
    fob_price = fields.Float(string="CIF.Price", related='material_line_id.fob_price', digits=(16, 3), help="Giá mua vào")
    exwork_price = fields.Float(string="EXW.Price", related='material_line_id.exwork_price', digits=(16, 3), help="Giá xuất xưởng")
    
