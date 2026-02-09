from odoo import models, fields, api
from odoo.exceptions import ValidationError, AccessError
import re

class GarmentCosting(models.Model):
    _name = 'garment.costing'
    _description = 'Costing Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'
    
# region (Phần 2) liên kết
    program_id = fields.Many2one('garment.program', required=True)
    style_id = fields.Many2one('garment.style', required=True)
    
    costing_line_ids = fields.One2many('garment.costing.line', 'costing_id', string='Costing Lines', help='Danh sách Costing Lines')
# endregion

# region (Phần 1) THÔNG TIN COSTING LINE  
    waste_percent = fields.Integer(string="Waste (%)", help="Phần trăm chi phí hao hụt", tracking=True)
    finance_percent = fields.Integer(string="Finance (%)", help="Phần trăm chi phí tài chính", tracking=True)
    
    waste = fields.Float(string="Waste", compute='_compute_waste_finance', store=True, help="Chi phí hao hụt", tracking=True)
    finance = fields.Float(string="Finance", compute='_compute_waste_finance', store=True, help="Chi phí tài chính", tracking=True)
    
    total_net = fields.Float(string="Total.Net", help="Tổng chi phí nguyên liệu", compute='_compute_total_net', store=True, tracking=True)
    
    cut_make = fields.Float(string="CM", help="Tiền công cắt, may, lắp ráp (CM)", tracking=True)
    
    admin_percent = fields.Integer(string="Admin (%)", help="Phần trăm chi phí quản lý, vận hành (Admin)", tracking=True)
    admin = fields.Float(string="Admin", compute='_compute_admin_cost', store=True, help="Chi phí quản lý, vận hành (Admin)", tracking=True)
    inspection_cost = fields.Float(string="Inspection.Cost", help="Chi phí kiểm hàng", tracking=True)
    test_cost = fields.Float(string="Test.Cost", help="Chi phí kiểm nghiệm", tracking=True)
    import_export_cost = fields.Float(string="Import/Export.Cost", help="Chi phí xuất nhập khẩu", tracking=True)
    
    standard_fob = fields.Float(string="Standard.FOB", help="Giá FOB cơ bản", compute='_compute_standard_fob', store=True, tracking=True)
    
    surcharge_percent = fields.Integer(string="Surcharge (%)", help="Phần trăm chi phí phụ thu", tracking=True)
    surcharge = fields.Float(string="Surcharge", compute='_compute_surcharge', store=True, help="Chi phí phụ thu", tracking=True)
    extra_cost = fields.Float(string="Extra.Cost", help="Chi phí phát sinh khác", tracking=True)
    
    final_fob = fields.Float(string="Final.FOB", help="Giá FOB cuối cùng", compute='_compute_final_fob', store=True, tracking=True)
    agreed_fob = fields.Float(string="Agreed.FOB", help="Giá FOB chốt", tracking=True)
    
    @api.constrains('waste_percent', 'finance_percent')
    def _check_percent_values(self):
        for record in self:
            if not (0 <= record.waste_percent <= 100):
                raise ValidationError("Tỷ lệ Waste (%) phải nằm trong khoảng từ 0 đến 100.")
            if not (0 <= record.finance_percent <= 100):
                raise ValidationError("Tỷ lệ Finance (%) phải nằm trong khoảng từ 0 đến 100.") 
            if not (0 <= record.admin_percent <= 100):
                raise ValidationError("Tỷ lệ Admin (%) phải nằm trong khoảng từ 0 đến 100.")  
            if not (0 <= record.surcharge_percent <= 100):
                raise ValidationError("Tỷ lệ Surcharge (%) phải nằm trong khoảng từ 0 đến 100.")                
              
            
    # tính toán phần trăm hao hụt tài chính       
    @api.depends('material_cost', 'waste_percent', 'finance_percent')
    def _compute_waste_finance(self):
        for rec in self:
            rec.waste = rec.material_cost * (rec.waste_percent / 100.0)
            rec.finance = rec.material_cost * (rec.finance_percent / 100.0)       
             
    # tính toán tổng giá trị cần thanh toán cho khách hàng
    @api.depends('material_cost', 'waste', 'finance')
    def _compute_total_net(self):
        for rec in self:
            rec.total_net = rec.material_cost + rec.waste + rec.finance
            
    # tính toán chi phí quản lý, vận hành (Admin)
    @api.depends('total_net', 'cut_make', 'admin_percent')
    def _compute_admin_cost(self):
        for rec in self:
            rec.admin = (rec.total_net + rec.cut_make) * (rec.admin_percent / 100.0)
            
    @api.depends('total_net', 'cut_make', 'admin', 'inspection_cost', 'test_cost', 'import_export_cost')
    def _compute_standard_fob(self):
        for rec in self:
            rec.standard_fob = (rec.total_net + 
                                rec.cut_make + 
                                rec.admin + 
                                rec.inspection_cost + 
                                rec.test_cost + 
                                rec.import_export_cost)
    # tính toán chi phí phụ thu
    @api.depends('standard_fob', 'surcharge_percent')
    def _compute_surcharge(self):
        for rec in self:
            rec.surcharge = rec.standard_fob * (rec.surcharge_percent / 100.0)

    @api.depends('standard_fob', 'surcharge', 'extra_cost')
    def _compute_final_fob(self):
        for rec in self:
            rec.final_fob = rec.standard_fob + rec.surcharge + rec.extra_cost
# endregion

# region (Phần 3) Các trường tính toán phụ trợ
    material_cost = fields.Float(string="Material.Cost", help ="Chi phí nguyên phụ liệu", compute='_compute_total_price', store=True, tracking=True)
    @api.depends('costing_line_ids.amount')
    def _compute_total_price(self):
        for record in self:
            record.material_cost = sum(line.amount for line in record.costing_line_ids)    
# endregion


class GarmentCostingLine(models.Model):
    _name = 'garment.costing.line'
    _description = 'Costing Line'

    # ======================
    # LIÊN KẾT BẮT BUỘC
    # ======================
    #costing_id = fields.Many2one('garment.costing', required=True)

    style_id = fields.Many2one('garment.style', required=True)
    #material_id = fields.Many2one('garment.material', required=True)
    
    style_material_id = fields.Many2one(
        'garment.style.material',
        string='Material',
        required=True,
        domain="[('style_id', '=', style_id)]"
    )

    material_id = fields.Many2one(
        related='style_material_id.material_id',
        store=True,
        readonly=True
    )
    # ======================
    # LINK NGUỒN DỮ LIỆU
    # ======================
    consumption_id = fields.Many2one('garment.consumption',compute='_compute_links',store=True)

    # ======================
    # GIÁ TRỊ ĐƯỢC LẤY TỰ ĐỘNG
    # ======================
    consumption_qty = fields.Float( related='consumption_id.est_qty', store=True, readonly=True)


    # ======================
    
    unit_price = fields.Float( string="Unit Price",store=True, )
    # THÀNH TIỀN
    # ======================
    amount = fields.Float(
        compute='_compute_amount',
        store=True
    )


    # ======================
    # LOGIC GHÉP DỮ LIỆU
    # ======================
    @api.depends('style_id', 'material_id', 'material_color_id')
    def _compute_links(self):
        for r in self:
            # 1. Consumption: theo style + material
            r.consumption_id = self.env['garment.consumption'].search([
                ('style_id', '=', r.style_id.id),
                ('material_id', '=', r.material_id.id)
            ], limit=1)

    # ======================
    # TÍNH TIỀN
    # ======================
    @api.depends('consumption_qty', 'order_qty', 'unit_price')
    def _compute_amount(self):
        for r in self:
            r.amount = (
                r.consumption_qty *
                r.unit_price
            )




