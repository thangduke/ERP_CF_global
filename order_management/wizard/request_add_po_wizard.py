from odoo import models, fields, api
from odoo.exceptions import UserError

class RequestAddPoWizard(models.TransientModel):
    _name = 'request.add.po.wizard'
    _description = 'Wizard Gửi Yêu Cầu Tạo Thêm PO'

    po_id = fields.Many2one('material.purchase.order', string='PO', required=True , invisible="1")
    line_ids = fields.One2many('material.invoice.create.wizard.line', 'wizard_po_id',
                        string='Dòng vật tư cần đặt hàng')
    supplier_id = fields.Many2one('supplier.partner', string='Nhà cung cấp')  # <-- Thêm dòng này
    entry_date = fields.Date(string="Ngày đặt hàng", default=fields.Datetime.now, required=True)

    approval_ids = fields.Many2many(
        'employee.base',
        string="Người duyệt",
        required=True,
        domain="[('id', 'in', allowed_approval_ids)]"
    )

    approval_note = fields.Text(string="Ghi chú gửi duyệt", required=True)
    
    allowed_approval_ids = fields.Many2many(
        'employee.base',
        string="Allowed Approvers",
        compute="_compute_allowed_approvers"
    )

    @api.depends('po_id')
    def _compute_allowed_approvers(self):
        for wizard in self:
            wizard.allowed_approval_ids = wizard.po_id.allowed_approval_ids

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        po = self.env['material.purchase.order'].browse(self._context.get('default_po_id'))
        lines = []
        supplier_id = po.supplier_id.id

        for po_line in po.line_ids.filtered(lambda line: line.supplier.id == supplier_id):
            total_received = sum(self.env['material.invoice.line'].search([
                ('po_line_id', '=', po_line.id)
            ]).mapped('act_qty'))
            remaining = po_line.est_qty - total_received
            lines.append((0, 0, {
                'material_line_id': po_line.id,
                'name': po_line.name,
                'est_qty': po_line.est_qty,
                'remaining_qty': remaining,
                'act_qty': remaining,
            }))
            
        res.update({
            'po_id': po.id,
            'supplier_id': supplier_id,
            'line_ids': lines,
        })
        return res
  
    def action_confirm(self):
        """
        Tạo hóa đơn vật tư, cập nhật số lượng và gửi yêu cầu duyệt.
        """
        self.ensure_one()
        po = self.po_id

       # Kiểm tra xem có số lượng âm không
        if any(line.act_qty == 0 for line in self.line_ids):
            raise UserError("vật tư đặt hàng đang có Số lượng(PO.Qty) bằng 0. Hãy chỉnh lại số lượng hoặc xóa vật tư")

        # Lọc ra các dòng có số lượng thực tế > 0 để tạo hóa đơn
        lines_to_invoice = self.line_ids.filtered(lambda l: l.act_qty > 0)

        # Kiểm tra xem có ít nhất một dòng có số lượng > 0 không
        if not lines_to_invoice:
            raise UserError("Bạn phải nhập số lượng đặt hàng (PO.Qty) lớn hơn 0 cho ít nhất một vật tư.")

        # Tạo hóa đơn vật tư
        invoice = self.env['material.invoice'].create({
            'po_id': po.id,
            'supplier': self.supplier_id.id,
            'order_id': po.order_id.id,
            'state': 'pending_approval',
            'priority': '2',
        })

        for line in lines_to_invoice:
            po_line = line.material_line_id
            # Tạo dòng hóa đơn vật tư
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

        # Logic gửi yêu cầu duyệt từ action_confirm_send
        if not self.approval_ids:
            raise UserError("Vui lòng chọn người duyệt trước khi gửi.")
        
        # Ghi người duyệt + ghi chú vào PO
        po.write({
            'approval_ids': [(6, 0, self.approval_ids.ids)],
            'note_approval': self.approval_note,
            'state_approval': 'pending_approval',
        })

        # Gửi thông báo cho người duyệt
        partner_ids = self.approval_ids.mapped('user_id.partner_id.id')
        po.message_post(
            body=f"<b>Yêu cầu tạo thêm PO</b><br>"
                 f"Chương trình: <b>{po.order_id.name}</b><br>"
                 f"Nhà cung cấp: <b>{po.name}</b><br>"
                 f"Người tạo: <b>{po.employee_id.name}</b><br>"
                 f"Ghi chú: {self.approval_note or '(Không có ghi chú)'}",
            partner_ids=partner_ids,
            subtype_id=self.env.ref('mail.mt_note').id,
            author_id=po.employee_id.user_id.partner_id.id
                if po.employee_id.user_id and po.employee_id.user_id.partner_id
                else None,
        )

      #  return {'type': 'ir.actions.client', 'tag': 'reload'}
