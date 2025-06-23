/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import {
    useX2ManyCrud,
    useOpenX2ManyRecord,
} from "@web/views/fields/relational_utils";
import { formatDate } from "@web/core/l10n/dates";
import { useService } from '@web/core/utils/hooks';
import { onWillStart } from "@odoo/owl";
import { CommonResumeListRenderer } from "../../views/resume_list_renderer";

export class Resume3CListRenderer extends CommonResumeListRenderer {
    get groupBy() {
        return 'line_type_id';
    }

    get colspan() {
        if (this.props.activeActions) {
            return 3;
        }
        return 2;
    }

    formatDate(date) {
        return formatDate(date);
    }

    setDefaultColumnWidths() {}
}
Resume3CListRenderer.template = 'Employee.Resume3CListRenderer';
Resume3CListRenderer.rowsTemplate = "Employee.Resume3CListRenderer.Rows";
Resume3CListRenderer.recordRowTemplate = "Employee.Resume3CListRenderer.RecordRow";


export class Resume3CX2ManyField extends X2ManyField  {

    setup() {
        super.setup()
        const { saveRecord, updateRecord } = useX2ManyCrud(
            () => this.list,
            this.isMany2Many
        );

        const openRecord = useOpenX2ManyRecord({
            resModel: this.list.resModel,
            activeField: this.activeField,
            activeActions: this.activeActions,
            getList: () => this.list,
            saveRecord: async (record) => {
                await saveRecord(record);
                await this.props.record.save();
            },
            updateRecord: updateRecord,
            withParentId: this.props.widget !== "many2many",
        });

        this._openRecord = (params) => {
            params.title = this.getWizardTitleName();
            openRecord({...params});
        };
    }

    getWizardTitleName() {
        return _t("Create a resume line");
    }

    async onAdd({ context, editable } = {}) {
        const employeeId = this.props.record.resModel === "res.users" ? this.props.record.data.employee_id[0] : this.props.record.resId;
        return super.onAdd({
            editable,
            context: {
                ...context,
                default_employee_id: employeeId,
            }
        });
    }
}
Resume3CX2ManyField.components = {
    ...X2ManyField.components,
    ListRenderer: Resume3CListRenderer,
};

export const resume3CX2ManyField = {
    ...x2ManyField,
    component: Resume3CX2ManyField,
};

registry.category("fields").add("resume3c_one2many", resume3CX2ManyField);
