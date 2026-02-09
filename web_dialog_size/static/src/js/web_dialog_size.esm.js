/** @odoo-module **/

import {ActionDialog} from "@web/webclient/actions/action_dialog";
import {Component, onMounted} from "@odoo/owl";
import {Dialog} from "@web/core/dialog/dialog";
import {SelectCreateDialog} from "@web/views/view_dialogs/select_create_dialog";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";

export class ExpandButton extends Component {
    setup() {
        this.orm = useService("orm");
        this.last_size = this.props.getsize() || 'md'; // Default to medium size
        this.config = this.orm.call(
            "ir.config_parameter",
            "get_web_dialog_size_config"
        );
    }

    dialog_button_extend() {
        this.last_size = this.props.getsize() || 'md';
        this.props.setsize("dialog_full_screen");
        this.render();
    }

    dialog_button_restore() {
        this.props.setsize(this.last_size);
        this.render();
    }
}

ExpandButton.template = "web_dialog_size.ExpandButton";

patch(Dialog.prototype, {
    setup() {
        super.setup();
        this.setSize = this.setSize.bind(this);
        this.getSize = this.getSize.bind(this);
        // Set initial size to medium
        this.props.size = this.props.size || 'md';
    },

    setSize(size) {
        this.props.size = size;
        this.render();
    },

    getSize() {
        return this.props.size;
    },
});

patch(SelectCreateDialog.prototype, {
    setup() {
        super.setup();
        this.setSize = this.setSize.bind(this);
        this.getSize = this.getSize.bind(this);
    },

    setSize(size) {
        this.props.size = size;
        this.render();
    },

    getSize() {
        return this.props.size;
    },
});

Object.assign(ActionDialog.components, {ExpandButton});
SelectCreateDialog.components = Object.assign(SelectCreateDialog.components || {}, {
    ExpandButton,
});
Dialog.components = Object.assign(Dialog.components || {}, {ExpandButton});
// Patch annoying validation method
Dialog.props.size.validate = (s) =>
    ["sm", "md", "lg", "xl", "dialog_full_screen"].includes(s);
