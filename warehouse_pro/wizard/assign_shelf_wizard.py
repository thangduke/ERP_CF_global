from odoo import models, fields, api

class AssignShelfWizard(models.TransientModel):
    _name = 'assign.shelf.wizard'
    _description = 'Gán kệ cho vật tư'

    store_id = fields.Many2one('store.list', string='Kho', required=True, readonly=True)
    shelf_id = fields.Many2one('shelf.list', string='Kệ hàng', domain="[('store_id', '=', store_id)]", required=True)
    shelf_level_id = fields.Many2one('shelf.level', string='Khoang', domain="[('shelf_id', '=', shelf_id)]", required=True)


    selected_material_line_ids = fields.Many2many(
        'material.stock.summary', 
        string="Vật tư được chọn",
        compute='_compute_selected_material_lines',
        store=False,
    )

    @api.depends('store_id')
    def _compute_selected_material_lines(self):
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            # If launched from a selection of records
            self.selected_material_line_ids = self.env['material.stock.summary'].browse(active_ids)
        else:
            # Fallback if not launched from a context with active_ids
            for wizard in self:
                wizard.selected_material_line_ids = self.env['material.stock.summary'].search([
                    ('is_selected', '=', True),
                    ('store_id', '=', wizard.store_id.id)
                ])

    def action_assign(self):
        self.ensure_one()
        if not self.selected_material_line_ids:
            return # Or raise a user-friendly error
            
        # Use write for better performance on batch updates
        self.selected_material_line_ids.write({
            'shelf_id': self.shelf_id.id,
            'shelf_level_id': self.shelf_level_id.id,
            'is_selected': False # Uncheck after assigning
        })
        
        return {'type': 'ir.actions.act_window_close'}
