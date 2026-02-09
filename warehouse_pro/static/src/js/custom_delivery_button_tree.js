/** @odoo-module */
import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
export class MaterialListController extends ListController {
   setup() {
       super.setup();
   }
   OnTestClick() {
       this.actionService.doAction({
          type: 'ir.actions.act_window',
          res_model: 'delivery.style.wizard',
          name:'Tạo Phiếu Xuất Kho',
          view_mode: 'form',
          view_type: 'form',
          views: [[false, 'form']],
          target: 'new',
          res_id: false,
      });
   }
}
registry.category("views").add("button_delivery_tree", {
   ...listView,
   Controller: MaterialListController,
   buttonTemplate: "custom_delivery_button.ListView.Buttons",
});
