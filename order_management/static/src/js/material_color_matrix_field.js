/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { onMounted, onPatched, onWillUnmount, Component, useRef, xml, useState } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import "@web/views/fields/html/html_field";
const htmlField = registry.category("fields").get("html");

export class MaterialColorPickerPopover extends Component {
    static template = "order_management.MaterialColorPickerPopover";
    static props = ["close", "colors", "onSelectColor"];
    setup() {
        this.state = useState({ filteredColors: this.props.colors });
    }
    _onSearchInput(ev) {
        const searchTerm = ev.target.value.toLowerCase();
        this.state.filteredColors = searchTerm
            ? this.props.colors.filter(c =>
                (c.display_name || "").toLowerCase().includes(searchTerm) ||
                (c.color_name || "").toLowerCase().includes(searchTerm)
              )
            : this.props.colors;
    }
    _onSelectColor(colorId) {
        console.log("[MaterialColorPickerPopover] Selected materialColorId =", colorId);
        this.props.onSelectColor(colorId);
        this.props.close();
    }
}

export class MaterialColorMatrixField extends Component {
    static template = xml`<div t-ref="root" class="o_field_html_viewer"/>`;
    static components = { Popover: MaterialColorPickerPopover };
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.popover = usePopover(this.constructor.components.Popover);
        this.rootRef = useRef("root");

        this._delegatedClick = async (ev) => {
            const root = this.rootRef.el;
            if (!root) return;

            const colorCell = ev.target.closest('.color-cell');
            if (colorCell && root.contains(colorCell)) {
                const programCustomerId = colorCell.dataset.programCustomerId || colorCell.dataset.programcustomerid;
                const styleColorId = colorCell.dataset.styleColorId || colorCell.dataset.stylecolorid;

                console.log("[Click color-cell] Data:", { programCustomerId, styleColorId });

                if (!programCustomerId || !styleColorId) {
                    console.warn("[Click color-cell] Missing programCustomerId or styleColorId, skipping.");
                    return;
                }

                ev.preventDefault();

                const materialColors = await this.orm.searchRead("material.color", [], ["id", "display_name", "color_name"]);

                this.popover.open(colorCell, {
                    colors: materialColors,
                    onSelectColor: (materialColorId) => {
                        console.log("[Popover select] Calling updateColor with:", { programCustomerId, styleColorId, materialColorId });
                        this.updateColor(programCustomerId, styleColorId, materialColorId);
                    },
                });
                return;
            }

            const sizeCell = ev.target.closest('.size-cell');
            if (sizeCell && root.contains(sizeCell)) {
                const programCustomerId = sizeCell.dataset.programCustomerId || sizeCell.dataset.programcustomerid;
                const sizeId = sizeCell.dataset.sizeId || sizeCell.dataset.sizeid;
                const isChecked = (sizeCell.dataset.isChecked || sizeCell.dataset.ischecked) === '1';

                console.log("[Click size-cell]", { programCustomerId, sizeId, isChecked });
                if (!programCustomerId || !sizeId) return;

                ev.preventDefault();
                this.updateSize(programCustomerId, sizeId, !isChecked);
            }
            const toggleAll = ev.target.closest('.size-toggle-all');
            if (toggleAll && root.contains(toggleAll)) {
                ev.preventDefault();
                ev.stopPropagation();
                this._onToggleAllSizes(toggleAll);
            }

            const applyAllColors = ev.target.closest('.color-toggle-all-apply');
            if (applyAllColors && root.contains(applyAllColors)) {
                ev.preventDefault();
                ev.stopPropagation();
                this._onApplyAllColors(applyAllColors);
            }

            const clearAllColors = ev.target.closest('.color-toggle-all-clear');
            if (clearAllColors && root.contains(clearAllColors)) {
                ev.preventDefault();
                ev.stopPropagation();
                this._onClearAllColors(clearAllColors);
            }
        };

        this._renderHtml = () => {
            const rootEl = this.rootRef.el;
            if (!rootEl) return;
            const rawHtml = this.props.record.data[this.props.name] || "";
            if (rootEl.innerHTML !== rawHtml) {
                rootEl.innerHTML = rawHtml;
            }
        };

        onMounted(() => {
            console.log("[Mounted] MaterialColorMatrixField mounted, record =", this.props.record);
            this._renderHtml();
            const rootEl = this.rootRef.el;
            if (rootEl) rootEl.addEventListener('click', this._delegatedClick);
        });
        onPatched(() => {
            this._renderHtml();
        });
        onWillUnmount(() => {
            const rootEl = this.rootRef.el;
            if (rootEl) rootEl.removeEventListener('click', this._delegatedClick);
        });
    }
    async _onApplyAllColors(target) {
        try {
            await this.props.record.save({ stayInEdition: true });
            const wizardId = this.props.record.resId;
            if (!wizardId) {
                console.error("[_onApplyAllColors] Could not get wizard ID after save.");
                return;
            }

            const styleColorId = target.dataset.styleColorId;
            const root = this.rootRef.el;
            if (!root) return;
            const matrixWrapper = root.querySelector('.matrix-wrapper');
            if (!matrixWrapper) {
                console.error("[_onApplyAllColors] .matrix-wrapper not found");
                return;
            }
            const currentLines = matrixWrapper.dataset.lines;
            if (!currentLines) {
                console.error("[_onApplyAllColors] data-lines attribute not found on .matrix-wrapper");
                return;
            }

            const kwargs = {
                current_lines: currentLines,
                style_color_id: parseInt(styleColorId),
            };

            console.log("[_onApplyAllColors] Sending RPC with:", { wizardId, ...kwargs });

            const newHtml = await this.orm.call(
                this.props.record.resModel,
                "auto_apply_color_for_column",
                [wizardId],
                kwargs
            );

            console.log("[_onApplyAllColors] RPC success. New HTML received.");

            if (this.props.record.data[this.props.name] !== newHtml) {
                await this.props.record.update({ [this.props.name]: newHtml });
                console.log("[_onApplyAllColors] Updated UI with new HTML.");
            }
            await this._syncLinesFromHtml(newHtml, wizardId);

        } catch (err) {
            console.error("[_onApplyAllColors] RPC auto_apply_color_for_column failed:", err);
        }
    }

    async _onClearAllColors(target) {
        try {
            await this.props.record.save({ stayInEdition: true });
            const wizardId = this.props.record.resId;
            if (!wizardId) {
                console.error("[_onClearAllColors] Could not get wizard ID after save.");
                return;
            }

            const styleColorId = target.dataset.styleColorId;
            const root = this.rootRef.el;
            if (!root) return;
            const matrixWrapper = root.querySelector('.matrix-wrapper');
            if (!matrixWrapper) {
                console.error("[_onClearAllColors] .matrix-wrapper not found");
                return;
            }
            const currentLines = matrixWrapper.dataset.lines;
            if (!currentLines) {
                console.error("[_onClearAllColors] data-lines attribute not found on .matrix-wrapper");
                return;
            }

            const kwargs = {
                current_lines: currentLines,
                style_color_id: parseInt(styleColorId),
            };

            console.log("[_onClearAllColors] Sending RPC with:", { wizardId, ...kwargs });

            const newHtml = await this.orm.call(
                this.props.record.resModel,
                "clear_all_colors_for_column",
                [wizardId],
                kwargs
            );

            console.log("[_onClearAllColors] RPC success. New HTML received.");

            if (this.props.record.data[this.props.name] !== newHtml) {
                await this.props.record.update({ [this.props.name]: newHtml });
                console.log("[_onClearAllColors] Updated UI with new HTML.");
            }
            await this._syncLinesFromHtml(newHtml, wizardId);

        } catch (err) {
            console.error("[_onClearAllColors] RPC clear_all_colors_for_column failed:", err);
        }
    }
    
    async _onToggleAllSizes(target) {
        try {
            await this.props.record.save({ stayInEdition: true });
            const wizardId = this.props.record.resId;

            if (!wizardId) {
                console.error("[_onToggleAllSizes] Could not get wizard ID after save.");
                return;
            }

            const sizeId = target.dataset.sizeId;
            const isSelected = target.dataset.select === '1';

            const root = this.rootRef.el;
            if (!root) return;
            const matrixWrapper = root.querySelector('.matrix-wrapper');
            if (!matrixWrapper) {
                console.error("[_onToggleAllSizes] .matrix-wrapper not found");
                return;
            }
            const currentLines = matrixWrapper.dataset.lines;
            if (!currentLines) {
                console.error("[_onToggleAllSizes] data-lines attribute not found on .matrix-wrapper");
                return;
            }

            const kwargs = {
                current_lines: currentLines,
                size_id: parseInt(sizeId),
                is_selected: isSelected,
            };

            console.log("[_onToggleAllSizes] Sending RPC with:", { wizardId, ...kwargs });

            const newHtml = await this.orm.call(
                this.props.record.resModel,
                "toggle_all_sizes_for_column",
                [wizardId],
                kwargs
            );

            console.log("[_onToggleAllSizes] RPC success. New HTML received.");

            if (this.props.record.data[this.props.name] !== newHtml) {
                await this.props.record.update({ [this.props.name]: newHtml });
                console.log("[_onToggleAllSizes] Updated UI with new HTML.");
            }

            // Sync the full lines data with the server so action_apply has the correct data
            const newRoot = document.createElement('div');
            newRoot.innerHTML = newHtml;
            const newMatrixWrapper = newRoot.querySelector('.matrix-wrapper');
            if (newMatrixWrapper && newMatrixWrapper.dataset.lines) {
                const linesData = newMatrixWrapper.dataset.lines;
                console.log("[_onToggleAllSizes] Syncing lines data to server...");
                await this.orm.call(
                    this.props.record.resModel,
                    "sync_lines_before_action",
                    [wizardId],
                    { full_lines_json: linesData }
                );
                console.log("[_onToggleAllSizes] Lines data synced successfully.");
            } else {
                console.warn("[_onToggleAllSizes] Could not find new lines data in returned HTML to sync.");
            }
        } catch (err) {
            console.error("[_onToggleAllSizes] RPC toggle_all_sizes_for_column failed:", err);
        }
    }


    async _getWizardId() {
        let wizardId = this.props.record.resId;
        if (!wizardId) {
            console.warn("[_getWizardId] Chưa có wizardId, thực hiện save...");
            try {
                await this.props.record.save({ stayInEdition: true });
                wizardId = this.props.record.resId;
                console.log("[_getWizardId] Sau khi save có wizardId =", wizardId);
            } catch (error) {
                console.error("[_getWizardId] Lỗi khi save wizard:", error);
                return null;
            }
        }
        return wizardId;
    }

    async updateColor(programCustomerId, styleColorId, materialColorId) {
        try {
            await this.props.record.save({ stayInEdition: true });
            const wizardId = this.props.record.resId;
            if (!wizardId) {
                console.error("[updateColor] Could not get wizard ID after save.");
                return;
            }

            const root = this.rootRef.el;
            if (!root) return;
            const matrixWrapper = root.querySelector('.matrix-wrapper');
            if (!matrixWrapper) {
                console.error("[updateColor] .matrix-wrapper not found");
                return;
            }
            const currentLines = matrixWrapper.dataset.lines;
            if (!currentLines) {
                console.error("[updateColor] data-lines attribute not found on .matrix-wrapper");
                return;
            }

            const kwargs = {
                program_customer_id: parseInt(programCustomerId),
                style_color_id: parseInt(styleColorId),
                material_color_id: materialColorId,
                current_lines: currentLines,
            };

            console.log("[updateColor] Sending RPC with:", { wizardId, ...kwargs });

            const newHtml = await this.orm.call(
                this.props.record.resModel,
                "update_color_map",
                [wizardId],
                kwargs
            );

            console.log("[updateColor] RPC success. New HTML received.");

            if (this.props.record.data[this.props.name] !== newHtml) {
                await this.props.record.update({ [this.props.name]: newHtml });
                console.log("[updateColor] Updated UI with new HTML.");
            }

            // Sync the full lines data with the server so action_apply has the correct data
            const newRoot = document.createElement('div');
            newRoot.innerHTML = newHtml;
            const newMatrixWrapper = newRoot.querySelector('.matrix-wrapper');
            if (newMatrixWrapper && newMatrixWrapper.dataset.lines) {
                const linesData = newMatrixWrapper.dataset.lines;
                console.log("[updateColor] Syncing lines data to server...");
                await this.orm.call(
                    this.props.record.resModel,
                    "sync_lines_before_action",
                    [wizardId],
                    { full_lines_json: linesData }
                );
                console.log("[updateColor] Lines data synced successfully.");
            } else {
                console.warn("[updateColor] Could not find new lines data in returned HTML to sync.");
            }
        } catch (err) {
            console.error("[updateColor] RPC update_color_map failed:", err);
        }
    }

    async updateSize(programCustomerId, sizeId, isSelected) {
        try {
            await this.props.record.save({ stayInEdition: true });
            const wizardId = this.props.record.resId;

            if (!wizardId) {
                console.error("[updateSize] Could not get wizard ID after save.");
                return;
            }

            const root = this.rootRef.el;
            if (!root) return;
            const matrixWrapper = root.querySelector('.matrix-wrapper');
            if (!matrixWrapper) {
                console.error("[updateSize] .matrix-wrapper not found");
                return;
            }
            const currentLines = matrixWrapper.dataset.lines;
            if (!currentLines) {
                console.error("[updateSize] data-lines attribute not found on .matrix-wrapper");
                return;
            }

            const kwargs = {
                program_customer_id: parseInt(programCustomerId),
                size_id: parseInt(sizeId),
                is_selected: isSelected,
                current_lines: currentLines,
            };

            console.log("[updateSize] Sending RPC with:", { wizardId, ...kwargs });

            const newHtml = await this.orm.call(
                this.props.record.resModel,
                "update_size_selection",
                [wizardId],
                kwargs
            );

            console.log("[updateSize] RPC success. New HTML received.");

            if (this.props.record.data[this.props.name] !== newHtml) {
                await this.props.record.update({ [this.props.name]: newHtml });
                console.log("[updateSize] Updated UI with new HTML.");
            }

            // Sync the full lines data with the server so action_apply has the correct data
            const newRoot = document.createElement('div');
            newRoot.innerHTML = newHtml;
            const newMatrixWrapper = newRoot.querySelector('.matrix-wrapper');
            if (newMatrixWrapper && newMatrixWrapper.dataset.lines) {
                const linesData = newMatrixWrapper.dataset.lines;
                console.log("[updateSize] Syncing lines data to server...");
                await this.orm.call(
                    this.props.record.resModel,
                    "sync_lines_before_action",
                    [wizardId],
                    { full_lines_json: linesData }
                );
                console.log("[updateSize] Lines data synced successfully.");
            } else {
                console.warn("[updateSize] Could not find new lines data in returned HTML to sync.");
            }
        } catch (err) {
            console.error("[updateSize] RPC update_size_selection failed:", err);
        }
    }

}


export const materialColorMatrixField = {
    ...htmlField,
    component: MaterialColorMatrixField,
};

registry.category("fields").add("material_color_matrix_field", materialColorMatrixField);
