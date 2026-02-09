/** @odoo-module */
import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';

export class EmployeeListController extends ListController {
   setup() {
       super.setup();
   }

   OnImportClick() {
       this.actionService.doAction({
          type: 'ir.actions.act_window',
          res_model: 'employee.import.wizard',
          name:'Import Nhân sự',
          view_mode: 'form',
          view_type: 'form',
          views: [[false, 'form']],
          target: 'new',
          res_id: false,
      });
   }

   OnExportClick() {
        this.actionService.doAction('Employee.action_export_employee_list');
   }
}

registry.category("views").add("button_open_tree", {
   ...listView,
   Controller: EmployeeListController,
   buttonTemplate: "employee_button.ListView.Buttons",
});