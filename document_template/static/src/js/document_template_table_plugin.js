/** @odoo-module **/

import { Plugin } from "@html_editor/plugin";
import { isEmptyBlock } from "@html_editor/utils/dom_info";
import { closestElement } from "@html_editor/utils/dom_traversal";

/**
 * Keep empty table cells clickable: Odoo/contenteditable will not place the
 * caret in a bare <td></td>. Ensure every cell has a block with a <br>.
 */
export class DocumentTemplateTablePlugin extends Plugin {
    static id = "documentTemplateTable";
    static dependencies = ["baseContainer", "selection"];

    resources = {
        normalize_handlers: this.fillEmptyCells.bind(this),
    };

    setup() {
        this.addDomListener(this.editable, "pointerdown", this._onPointerDown.bind(this), true);
        this.fillEmptyCells();
    }

    _isCellEmpty(cell) {
        if (!cell) {
            return false;
        }
        if (cell.querySelector("img, table, video, iframe")) {
            return false;
        }
        const text = (cell.textContent || "").replace(/[\u200B\u00A0\s]/g, "");
        if (text) {
            return false;
        }
        const blocks = cell.querySelectorAll("p, div, h1, h2, h3, h4, h5, h6, li");
        if (!blocks.length) {
            return true;
        }
        return [...blocks].every((block) => isEmptyBlock(block));
    }

    _hasEditableShell(cell) {
        if (!cell?.firstElementChild) {
            return false;
        }
        if (cell.children.length !== 1) {
            return false;
        }
        const child = cell.firstElementChild;
        if (!["P", "DIV"].includes(child.nodeName)) {
            return false;
        }
        return Boolean(child.querySelector("br")) || isEmptyBlock(child);
    }

    /**
     * @returns {boolean} true if the cell DOM was replaced
     */
    _prepareCell(cell) {
        if (!this._isCellEmpty(cell)) {
            return false;
        }
        // Already has <p><br></p> (or equivalent): do not destroy the caret.
        if (this._hasEditableShell(cell)) {
            return false;
        }
        cell.replaceChildren();
        const baseContainer = this.dependencies.baseContainer.createBaseContainer();
        baseContainer.append(this.document.createElement("br"));
        cell.append(baseContainer);
        return true;
    }

    fillEmptyCells(root = this.editable) {
        if (!root?.querySelectorAll) {
            return;
        }
        for (const cell of root.querySelectorAll("td, th")) {
            this._prepareCell(cell);
        }
    }

    _onPointerDown(ev) {
        const cell = closestElement(ev.target, "td, th");
        if (!cell || !this.editable.contains(cell)) {
            return;
        }
        const replaced = this._prepareCell(cell);
        if (!replaced) {
            // Let the browser place the caret in the existing empty shell.
            return;
        }
        const target = cell.querySelector("p, div") || cell;
        const br = target.querySelector("br") || target;
        try {
            this.dependencies.selection.setCursorStart(br);
        } catch {
            try {
                this.dependencies.selection.setCursorStart(target);
            } catch {
                // ignore
            }
        }
    }
}
