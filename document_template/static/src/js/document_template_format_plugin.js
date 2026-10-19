/** @odoo-module **/

import { Plugin } from "@html_editor/plugin";
import { FontSelector } from "@html_editor/main/font/font_selector";
import { closestBlock, isBlock } from "@html_editor/utils/blocks";
import { formatsSpecs } from "@html_editor/utils/formatting";
import { closestPath, findNode } from "@html_editor/utils/dom_traversal";
import { withSequence } from "@html_editor/utils/resource";
import { reactive } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

const FONT_FAMILIES = [
    { name: "Arial", fontFamily: "Arial, Helvetica, sans-serif" },
    { name: "Times New Roman", fontFamily: "'Times New Roman', Times, serif" },
    { name: "Georgia", fontFamily: "Georgia, serif" },
    { name: "Courier New", fontFamily: "'Courier New', Courier, monospace" },
    { name: "Verdana", fontFamily: "Verdana, Geneva, sans-serif" },
    { name: "Tahoma", fontFamily: "Tahoma, Geneva, sans-serif" },
    { name: "Trebuchet MS", fontFamily: "'Trebuchet MS', sans-serif" },
    { name: "Comic Sans MS", fontFamily: "'Comic Sans MS', cursive" },
    { name: "Roboto", fontFamily: "Roboto, Arial, sans-serif" },
];

function ensureFontFamilyFormat() {
    if (formatsSpecs.fontFamily) {
        return;
    }
    formatsSpecs.fontFamily = {
        isFormatted: (node) =>
            !!findNode(
                closestPath(node),
                (el) => el.style && el.style.fontFamily,
                isBlock
            ),
        hasStyle: (node) => node.style && node.style.fontFamily,
        addStyle: (node, props) => {
            node.style.fontFamily = props.fontFamily;
        },
        removeStyle: (node) => {
            node.style.fontFamily = null;
            if (node.getAttribute("style") === "") {
                node.removeAttribute("style");
            }
        },
    };
}

function isAligned(mode) {
    return (selection) => {
        const node = selection.anchorNode;
        if (!node) {
            return false;
        }
        const block = closestBlock(node);
        if (!block) {
            return false;
        }
        let textAlign = getComputedStyle(block).textAlign;
        if (textAlign === "start") {
            textAlign = "left";
        }
        if (textAlign === "end") {
            textAlign = "right";
        }
        return textAlign === mode;
    };
}

/**
 * Docs-like extras: font family dropdown + alignment buttons on the toolbar.
 */
export class DocumentTemplateFormatPlugin extends Plugin {
    static id = "documentTemplateFormat";
    static dependencies = ["format", "selection", "align"];

    resources = {
        toolbar_groups: [
            withSequence(15, { id: "font-family" }),
            withSequence(35, { id: "alignment" }),
        ],
        toolbar_items: [
            {
                id: "font-family",
                groupId: "font-family",
                title: _t("Font"),
                Component: FontSelector,
                props: {
                    getItems: () => FONT_FAMILIES,
                    getDisplay: () => this.fontFamilyState,
                    onSelected: (item) => this.applyFontFamily(item),
                },
            },
            {
                id: "align-left",
                groupId: "alignment",
                commandId: "alignLeft",
                title: _t("Align left"),
                icon: "fa-align-left",
                isActive: isAligned("left"),
            },
            {
                id: "align-center",
                groupId: "alignment",
                commandId: "alignCenter",
                title: _t("Align center"),
                icon: "fa-align-center",
                isActive: isAligned("center"),
            },
            {
                id: "align-right",
                groupId: "alignment",
                commandId: "alignRight",
                title: _t("Align right"),
                icon: "fa-align-right",
                isActive: isAligned("right"),
            },
            {
                id: "align-justify",
                groupId: "alignment",
                commandId: "justify",
                title: _t("Justify"),
                icon: "fa-align-justify",
                isActive: isAligned("justify"),
            },
        ],
        selectionchange_handlers: this.updateFontFamilyDisplay.bind(this),
        step_added_handlers: this.updateFontFamilyDisplay.bind(this),
    };

    setup() {
        ensureFontFamilyFormat();
        this.fontFamilyState = reactive({ displayName: _t("Font") });
        this.updateFontFamilyDisplay();
    }

    applyFontFamily(item) {
        this.dependencies.format.formatSelection("fontFamily", {
            applyStyle: true,
            formatProps: { fontFamily: item.fontFamily },
        });
        this.fontFamilyState.displayName = item.name;
        this.dependencies.selection.focusEditable();
    }

    updateFontFamilyDisplay() {
        let selection;
        try {
            selection = this.dependencies.selection.getEditableSelection();
        } catch {
            this.fontFamilyState.displayName = _t("Font");
            return;
        }
        const node = selection?.anchorNode;
        if (!node) {
            this.fontFamilyState.displayName = _t("Font");
            return;
        }
        const el =
            node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
        if (!el || !(el instanceof Element)) {
            this.fontFamilyState.displayName = _t("Font");
            return;
        }
        const computed = getComputedStyle(el).fontFamily || "";
        const match = FONT_FAMILIES.find((font) => {
            const first = font.fontFamily
                .split(",")[0]
                .replace(/['"]/g, "")
                .trim()
                .toLowerCase();
            return computed.toLowerCase().includes(first);
        });
        this.fontFamilyState.displayName = match ? match.name : _t("Font");
    }
}
