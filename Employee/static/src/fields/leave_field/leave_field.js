/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { formatFloat } from "@web/views/fields/formatters";
import { useInputField } from "@web/views/fields/input_field_hook";
import { useNumpadDecimal } from "@web/views/fields/numpad_decimal_hook";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component } from "@odoo/owl";

export class LeaveField extends Component {
    static template = "Employee.LeaveField";
    static props = {
        ...standardFieldProps,
        digits: { type: Array, optional: true },
        placeholder: { type: String, optional: true },
    };
    setup() {
        useInputField({
            getValue: () =>
                formatFloat(this.props.record.data[this.props.name], {
                    digits: this.digits,
                    noSymbol: true,
                }),
            refName: "numpadDecimal",
            parse: (v) => parseFloat(v),
        });
        useNumpadDecimal();
    }
    get digits() {
        const fieldDigits = this.props.record.fields[this.props.name].digits;
        return !this.props.digits && Array.isArray(fieldDigits) ? fieldDigits : this.props.digits;
    }

    get formattedValue() {
        return formatFloat(this.props.record.data[this.props.name], {
            digits: this.digits,
        });
    }
}

export const leaveField = {
    component: LeaveField,
    displayName: _t("Leave"),
    supportedTypes: ["integer", "float"],
    extractProps: ({ attrs, options }) => {
        // Sadly, digits param was available as an option and an attr.
        // The option version could be removed with some xml refactoring.
        let digits;
        if (attrs.digits) {
            digits = JSON.parse(attrs.digits);
        } else if (options.digits) {
            digits = options.digits;
        }

        return {
            digits,
            placeholder: attrs.placeholder,
        };
    },
};

registry.category("fields").add("leave_field", leaveField);
