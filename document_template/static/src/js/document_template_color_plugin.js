/** @odoo-module **/

import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { withSequence } from "@html_editor/utils/resource";

/**
 * When the caret is inside a table cell, the background / text color tools
 * paint the whole cell (like Google Docs), not only a <font> wrapper.
 * Multi-cell selection (.o_selected_td) stays handled by the core table plugin.
 */
export class DocumentTemplateColorPlugin extends Plugin {
    static id = "documentTemplateColor";
    static dependencies = ["color", "selection"];

    resources = {
        color_apply_overrides: withSequence(5, this.applyCurrentCellColor.bind(this)),
    };

    applyCurrentCellColor(color, mode, previewMode) {
        if (mode !== "backgroundColor" && mode !== "color") {
            return false;
        }
        const selectedTds = this.editable.querySelectorAll("td.o_selected_td, th.o_selected_td");
        if (selectedTds.length) {
            // Core TablePlugin handles multi-cell selection.
            return false;
        }
        const selection = this.dependencies.selection.getEditableSelection();
        const cell = closestElement(selection.anchorNode, "td, th");
        if (!cell || !this.editable.contains(cell)) {
            return false;
        }
        // Background always targets the cell. Text color targets the cell when
        // the caret is collapsed (typing color for the whole casilla).
        if (mode === "color" && !selection.isCollapsed) {
            return false;
        }
        // Core ColorPlugin appends 60% opacity for solid highlight; casillas need solid fills.
        if (mode === "backgroundColor" && /^#[0-9A-Fa-f]{8}$/.test(color || "")) {
            color = color.slice(0, 7);
        }
        cell.classList.toggle("o_selected_td_bg_color_preview", Boolean(previewMode));
        this.dependencies.color.colorElement(cell, color || "", mode);
        if (mode === "backgroundColor") {
            if (color) {
                const luminance = this._luminance(getComputedStyle(cell).backgroundColor);
                cell.style.color = luminance < 140 ? "#FFFFFF" : "";
            } else {
                cell.style.color = "";
            }
        }
        return true;
    }

    _luminance(cssColor) {
        const match = (cssColor || "").match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
        if (!match) {
            return 255;
        }
        const r = Number(match[1]);
        const g = Number(match[2]);
        const b = Number(match[3]);
        return 0.299 * r + 0.587 * g + 0.114 * b;
    }
}
