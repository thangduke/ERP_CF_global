/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { usePopover } from "@web/core/popover/popover_hook";
import { many2OneField, Many2OneField } from "@web/views/fields/many2one/many2one_field";

import { Component } from "@odoo/owl";
import { AvatarMany2XAutocomplete } from "@web/views/fields/relational_utils";

export class Many2OneEmployee3cField extends Component {
    static template = "Employee.Many2OneEmployee3cField";
    static components = {
        Many2OneField,
    };
    static props = {
        ...Many2OneField.props,
    };

    get relation() {
        return this.props.relation || this.props.record.fields[this.props.name].relation;
    }
    get many2OneProps() {
        return Object.fromEntries(
            Object.entries(this.props).filter(
                ([key, _val]) => key in this.constructor.components.Many2OneField.props
            )
        );
    }

     get employeeIndex() {
        return this.props.record.data.employee_id ? this.props.record.data.employee_id.employee_index : '';
    }

    get jobTitle() {
        return this.props.record.data.employee_id ? this.props.record.data.employee_id.job_title : '';
    }
}

export const many2OneEmployee3cField = {
    ...many2OneField,
    component: Many2OneEmployee3cField,
    extractProps(fieldInfo) {
        const props = many2OneField.extractProps(...arguments);
        props.canOpen = fieldInfo.viewType === "form";
        return props;
    },
};

export class Many2OneFieldPopover extends Many2OneField {
    static props = {
        ...Many2OneField.props,
        close: { type: Function },
    };
    static components = {
        Many2XAutocomplete: AvatarMany2XAutocomplete,
    };
    get Many2XAutocompleteProps() {
        return {
            ...super.Many2XAutocompleteProps,
            dropdown: false,
            autofocus: true,
        };
    }

    async updateRecord(value) {
        const updatedValue = await super.updateRecord(...arguments);
        await this.props.record.save();
        return updatedValue;
    }
}

registry.category("fields").add("many2one_employee3c", many2OneEmployee3cField);
