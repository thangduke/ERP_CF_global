/** @odoo-module */

import { Component } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class Employee3CStatus extends Component {
    static template = "Employee.Employee3CStatus";
    static props = {
        ...standardFieldProps,
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        tag: "h1",
    };

    get classNames() {
        const classNames = ["fa"];
        classNames.push(
            this.icon,
            "fa-fw",
            "fa-lg",
            "o_button_icon",
            "align-middle",
        )
        return classNames.join(" ");
    }

    get color() {
        switch (this.value) {
            case "probation":
                return "text-info";
            case "official":
                return "text-success";
            case "quit":
                return "text-muted";
            case "break":
                return "text-warning";
            default:
                return "";
        }
    }

    get customStyle() {
        switch (this.value) {
            case "probation":
                return "color: #06d001; ";
            case "official":
                return "color: #06d001; ";
            case "quit":
                return "color: #ff6969; ";
            case "break":
                return "color: #ff6969; ";
            default:
                return "color: #eeedeb;";
        }
    }

    get icon() {
         switch (this.value) {
            case "probation":
                return `fa-circle-thin`;
            case "break":
                return `fa-circle-thin`;
            default:
                return `fa-circle`
         }
    }

    get label() {
        return this.value !== false
            ? this.options.find(([value, label]) => value === this.value)[1]
            : "Không xác định";
    }

    get options() {
        return this.props.record.fields[this.props.name].selection.filter(
            (option) => option[0] !== false && option[1] !== ""
        );
    }

    get value() {
        return this.props.record.data[this.props.name];
    }
}

export const employee3cStatus = {
    component: Employee3CStatus,
    displayName: _t("Employee Status"),
    extractProps({ viewType }, dynamicInfo) {
        return {
            tag: viewType === "kanban" ? "span" : "h1"
        };
    },
};

registry.category("fields").add("employee3c_status", employee3cStatus)
