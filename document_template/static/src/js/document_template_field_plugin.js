/** @odoo-module **/

import { Plugin } from "@html_editor/plugin";
import { DynamicPlaceholderPlugin } from "@html_editor/others/dynamic_placeholder_plugin";
import { closestElement, selectElements } from "@html_editor/utils/dom_traversal";
import { withSequence } from "@html_editor/utils/resource";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { DocumentTemplateFieldInfoPopover } from "./document_template_field_info_popover";

const FIELD_ATTRS = ["t-out", "t-esc", "t-raw", "t-field"];
const FIELD_SELECTOR = FIELD_ATTRS.map((attr) => `[${attr}]`).join(", ");

/**
 * Prefer meaningful labels:
 * - object._contract_text(object.vendor_id.name, …) → vendor_id.name
 * - object._contract_asset_value('accessories', …) → accessories
 * - object._contract_amount(line['amount_balance'], …) → amount_balance
 *
 * Important: never treat `_contract_amount(` as a field path. The naive
 * `object.X(?!\()` regex backtracks to `_contract_amoun` and that truncated
 * helper name was what chips showed in the editor.
 */
function extractPrimaryFieldPath(expression) {
    // Ignore the boolean condition of ternaries: `EXPR if COND else …`
    const text = String(expression || "").split(/\s+if\s+/)[0];
    // Skip `_contract_*` helpers; require the path is not a method call
    // (`(?![\w.]*\s*\()` blocks backtracking into `_contract_amoun`).
    const re =
        /\bobject\.((?!_contract_)[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)*)(?![\w.]*\s*\()/g;
    let match;
    let first = null;
    let best = null;
    while ((match = re.exec(text))) {
        const path = match[1];
        if (!first) {
            first = path;
        }
        if (!best || path.split(".").length > best.split(".").length) {
            best = path;
        }
    }
    return best || first || "";
}

function isBlankPlaceholder(value) {
    return !value || /^[_\s.\-\/]+$/.test(value) || value.length >= 40;
}

function extractDictKey(expression) {
    const match = String(expression || "").match(/\[['"]([a-zA-Z_]\w*)['"]\]/);
    return match ? match[1] : "";
}

/**
 * Useful string literals in helpers (skip blanks like ____________).
 * Examples: 'accessories', 'amount_capital', 'x_kyc_funds_origin'
 */
function extractUsefulStringKeys(expression) {
    const keys = [];
    const re = /(['"])([^'"]+)\1/g;
    let match;
    while ((match = re.exec(String(expression || "")))) {
        const value = match[2];
        if (isBlankPlaceholder(value)) {
            continue;
        }
        // Prefer technical codes / field names; skip comparison literals
        if (!/^[a-zA-Z_][\w.]*$/.test(value)) {
            continue;
        }
        if (["natural", "legal", "si", "no", "true", "false"].includes(value)) {
            continue;
        }
        keys.push(value);
    }
    return keys;
}

function extractHelperHint(expression) {
    let cleaned = String(expression || "").trim();
    if (cleaned.startsWith("object.")) {
        cleaned = cleaned.slice("object.".length);
    }
    const methodMatch = cleaned.match(/^(_contract_[a-zA-Z_]\w*|[a-zA-Z_]\w*)\s*\(/);
    if (!methodMatch) {
        return "";
    }
    let name = methodMatch[1];
    if (name.startsWith("_contract_")) {
        name = name.slice("_contract_".length);
    }
    return name;
}

/**
 * Nested helpers: `_contract_amount(object._contract_ves_rate(), …)` → ves_rate
 */
function extractNestedHelperHint(expression) {
    const names = [];
    const re = /_contract_([a-zA-Z_]\w*)\s*\(/g;
    let match;
    while ((match = re.exec(String(expression || "")))) {
        names.push(match[1]);
    }
    if (names.length < 2) {
        return "";
    }
    // Prefer the innermost (last) helper name
    return names[names.length - 1] || "";
}

/**
 * `object._contract_representatives(…)[:1].name` → name
 */
function extractChainedAttr(expression) {
    const text = String(expression || "");
    const sliceAttr = text.match(
        /\)\s*\[\s*:?\s*\d*\s*\]\s*\.\s*([a-zA-Z_]\w*)/
    );
    if (sliceAttr) {
        return sliceAttr[1];
    }
    const mapped = text.match(/\.mapped\(\s*['"]([a-zA-Z_]\w*)['"]\s*\)/);
    if (mapped) {
        return mapped[1];
    }
    return "";
}

function truncatePath(path) {
    if (!path) {
        return "…";
    }
    if (path.length <= 32) {
        return path;
    }
    const parts = path.split(".").filter(Boolean);
    if (parts.length >= 2) {
        return `…${parts.slice(-2).join(".")}`;
    }
    return `…${path.slice(-28)}`;
}

/**
 * Short editor label for long QWeb expressions so table cells keep their layout.
 * Shows the field / asset code, not a truncated helper name.
 */
export function shortFieldLabel(expression) {
    if (!expression) {
        return "…";
    }
    const raw = String(expression).trim();
    const hint = extractHelperHint(raw);
    const stringKeys = extractUsefulStringKeys(raw);

    // _contract_asset_value('accessories'), selection field names, installment totals
    // Also when nested: amount(installment_total('amount_capital'))
    if (
        ["asset_value", "installment_total", "selection"].includes(hint) &&
        stringKeys.length
    ) {
        return truncatePath(stringKeys[0]);
    }
    if (stringKeys.length && extractNestedHelperHint(raw) === "installment_total") {
        return truncatePath(stringKeys[0]);
    }

    const dictKey = extractDictKey(raw);
    if (dictKey) {
        return truncatePath(dictKey);
    }

    const chainedAttr = extractChainedAttr(raw);
    if (chainedAttr) {
        return truncatePath(chainedAttr);
    }

    const innerPath = extractPrimaryFieldPath(raw);
    if (innerPath) {
        return truncatePath(innerPath);
    }

    if (stringKeys.length) {
        return truncatePath(stringKeys[0]);
    }

    const nested = extractNestedHelperHint(raw);
    if (nested) {
        return truncatePath(nested);
    }

    let cleaned = raw;
    if (cleaned.startsWith("object.")) {
        cleaned = cleaned.slice("object.".length);
    }
    if (!cleaned.includes("(")) {
        return truncatePath(cleaned);
    }

    if (hint) {
        return truncatePath(hint);
    }
    return truncatePath(cleaned.split("(")[0] || cleaned);
}

export function decorateFieldChip(el, expression) {
    if (!el || !expression) {
        return;
    }
    const label = shortFieldLabel(expression);
    el.setAttribute("data-oe-field-label", label);
    el.removeAttribute("title");
}

function expressionFromNode(el) {
    for (const attr of FIELD_ATTRS) {
        if (el.hasAttribute(attr)) {
            return { directive: attr, expression: el.getAttribute(attr) || "" };
        }
    }
    return { directive: "", expression: "" };
}

function parseExpressionMeta(expression) {
    const raw = String(expression || "").trim();
    let cleaned = raw;
    if (cleaned.startsWith("object.")) {
        cleaned = cleaned.slice("object.".length);
    }
    const stringKeys = extractUsefulStringKeys(raw);
    const path =
        extractDictKey(raw) ||
        extractPrimaryFieldPath(raw) ||
        stringKeys[0] ||
        "";
    const methodMatch = cleaned.match(/^([a-zA-Z_][\w.]*)\s*\(/);
    if (methodMatch) {
        return { path, method: methodMatch[1] };
    }
    return { path: path || cleaned, method: "" };
}

function fieldInfoPropsFromNode(el) {
    const { directive, expression } = expressionFromNode(el);
    const label =
        el.getAttribute("data-oe-field-label") || shortFieldLabel(expression);
    const { path, method } = parseExpressionMeta(expression);
    const defaultValue = (el.textContent || "").replace(/\u200B/g, "").trim();
    return {
        label,
        expression,
        directive: directive || "t-out",
        path: path || "",
        method: method || "",
        defaultValue: defaultValue || "",
    };
}

/**
 * Puts "Field" first in the `/` powerbox so users can insert Odoo fields
 * instead of only format/markdown-like commands. Also shows field details
 * on hover/click of a chip.
 */
export class DocumentTemplateFieldPlugin extends Plugin {
    static id = "documentTemplateField";
    static dependencies = ["userCommand", "selection", "overlay"];

    resources = {
        powerbox_categories: withSequence(1, {
            id: "document_fields",
            name: _t("Fields"),
        }),
        powerbox_items: {
            categoryId: "document_fields",
            commandId: "insertDocumentField",
        },
        user_commands: {
            id: "insertDocumentField",
            title: _t("Field"),
            description: _t("Insert a field from the selected model"),
            keywords: [
                "field",
                "campo",
                "placeholder",
                "variable",
                "dato",
                "merge",
                "object",
            ],
            icon: "fa-hashtag",
            run: this.insertField.bind(this),
        },
        normalize_handlers: this.normalizeFieldChips.bind(this),
    };

    setup() {
        this._hoverTimer = null;
        this._pinned = false;
        this._currentNode = null;
        this._onDocPointerDown = this._onDocPointerDown.bind(this);
        this._onClick = this._onClick.bind(this);
        this._onPointerOver = this._onPointerOver.bind(this);
        this._onPointerOut = this._onPointerOut.bind(this);
        this.infoOverlay = this.dependencies.overlay.createOverlay(
            DocumentTemplateFieldInfoPopover,
            {
                closeOnPointerdown: false,
                className: "o_document_template_field_info_overlay",
                positionOptions: {
                    // Prefer below the chip: EditorOverlay hides overlays that
                    // sit above the scroll container top edge.
                    position: "bottom",
                    onPositioned: (el, { direction }) => {
                        el.classList.remove(
                            "bs-popover-top",
                            "bs-popover-bottom",
                            "bs-popover-start",
                            "bs-popover-end"
                        );
                        el.classList.add(`bs-popover-${direction}`);
                        el.style.visibility = "visible";
                    },
                },
            }
        );
        // Native listeners: addDomListener skips protected QWeb field chips.
        this.editable.addEventListener("click", this._onClick, true);
        this.editable.addEventListener("pointerover", this._onPointerOver);
        this.editable.addEventListener("pointerout", this._onPointerOut);
        document.addEventListener("pointerdown", this._onDocPointerDown, true);
        this._cleanups.push(() => {
            this.editable.removeEventListener("click", this._onClick, true);
            this.editable.removeEventListener("pointerover", this._onPointerOver);
            this.editable.removeEventListener("pointerout", this._onPointerOut);
            document.removeEventListener("pointerdown", this._onDocPointerDown, true);
        });
    }

    destroy() {
        this._clearHoverTimer();
        this.infoOverlay?.close();
        super.destroy();
    }

    /**
     * Allow listening to clicks on protected QWeb field nodes (t-out / t-esc…).
     */
    isValidTargetForDomListener(ev) {
        if (ev.target && closestElement(ev.target, FIELD_SELECTOR)) {
            return true;
        }
        return super.isValidTargetForDomListener(ev);
    }

    insertField() {
        return this.dependencies.userCommand
            .getCommand("openDynamicPlaceholder")
            .run();
    }

    normalizeFieldChips(root = this.editable) {
        if (!root?.querySelectorAll) {
            return;
        }
        for (const el of selectElements(root, FIELD_SELECTOR)) {
            const { expression } = expressionFromNode(el);
            if (!expression) {
                continue;
            }
            if (el.getAttribute("data-oe-field-label") === shortFieldLabel(expression)) {
                continue;
            }
            decorateFieldChip(el, expression);
        }
    }

    _fieldNodeFromEvent(ev) {
        const target = ev.target;
        if (!target?.closest) {
            return null;
        }
        const node = closestElement(target, FIELD_SELECTOR);
        if (!node || !this.editable.contains(node)) {
            return null;
        }
        return node;
    }

    _openInfo(node, { pinned = false } = {}) {
        if (!node) {
            return;
        }
        this._pinned = pinned;
        this._currentNode = node;
        // Overlay.open() only updates position if already open; reopen for new props.
        if (this.infoOverlay.isOpen) {
            this.infoOverlay.close();
        }
        const props = fieldInfoPropsFromNode(node);
        this.infoOverlay.open({
            target: node,
            props: {
                ...props,
                close: () => this._closeInfo(),
            },
        });
    }

    _closeInfo() {
        this._pinned = false;
        this._currentNode = null;
        this._clearHoverTimer();
        if (this.infoOverlay?.isOpen) {
            this.infoOverlay.close();
        }
    }

    _clearHoverTimer() {
        if (this._hoverTimer) {
            clearTimeout(this._hoverTimer);
            this._hoverTimer = null;
        }
    }

    _onDocPointerDown(ev) {
        if (!this.infoOverlay?.isOpen) {
            return;
        }
        const target = ev.target;
        if (target?.closest?.(FIELD_SELECTOR)) {
            return;
        }
        if (target?.closest?.(".o_document_template_field_info_popover")) {
            return;
        }
        if (target?.closest?.(".o_document_template_field_info_overlay")) {
            return;
        }
        this._closeInfo();
    }

    _onClick(ev) {
        const node = this._fieldNodeFromEvent(ev);
        if (!node) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        if (this._pinned && this._currentNode === node) {
            this._closeInfo();
            return;
        }
        this._openInfo(node, { pinned: true });
    }

    _onPointerOver(ev) {
        const node = this._fieldNodeFromEvent(ev);
        if (!node || this._pinned) {
            return;
        }
        const related = ev.relatedTarget;
        if (related && node.contains(related)) {
            return;
        }
        this._clearHoverTimer();
        this._hoverTimer = setTimeout(() => {
            if (!this._pinned) {
                this._openInfo(node, { pinned: false });
            }
        }, 350);
    }

    _onPointerOut(ev) {
        if (this._pinned) {
            return;
        }
        const node = this._fieldNodeFromEvent(ev);
        const related = ev.relatedTarget;
        if (node && related && node.contains(related)) {
            return;
        }
        if (
            related?.closest?.(
                ".o_document_template_field_info_popover, .o_document_template_field_info_overlay"
            )
        ) {
            return;
        }
        this._clearHoverTimer();
        if (this.infoOverlay?.isOpen && !this._pinned) {
            this._closeInfo();
        }
    }
}

/**
 * Keep the caret where the user clicked (e.g. empty table cell) while the
 * field picker popover steals focus. In document templates, also attach a
 * short visible label so long expressions do not break table layout.
 */
patch(DynamicPlaceholderPlugin.prototype, {
    open(resModel) {
        const inDocumentTemplate = Boolean(
            this.editable?.closest(".o_document_template_editor")
        );
        if (inDocumentTemplate) {
            this._documentTemplateCursor =
                this.dependencies.selection.preserveSelection();
        } else {
            this._documentTemplateCursor = null;
        }
        return super.open(...arguments);
    },

    onValidate(chain, defaultValue) {
        if (this._documentTemplateCursor) {
            this._documentTemplateCursor.restore();
            this._documentTemplateCursor = null;
        }
        const inDocumentTemplate = Boolean(
            this.editable?.closest(".o_document_template_editor")
        );
        if (!inDocumentTemplate || !chain) {
            return super.onValidate(...arguments);
        }
        const expression = `object.${chain}`;
        const t = document.createElement("T");
        t.setAttribute("t-out", expression);
        decorateFieldChip(t, expression);
        if (defaultValue?.length) {
            t.innerText = defaultValue;
        }
        this.dependencies.dom.insert(t);
        this.dependencies.history.addStep();
    },

    onClose() {
        this._documentTemplateCursor = null;
        return super.onClose(...arguments);
    },
});
