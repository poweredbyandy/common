/** @odoo-module **/

import { Chrome } from "@point_of_sale/app/pos_app";
import { patch } from "@web/core/utils/patch";
import { useExternalListener } from "@odoo/owl";

const EDITABLE_SELECTOR = "input, textarea, select, [contenteditable='true']";

function isEditableElement(el) {
    if (!el || !(el instanceof Element)) {
        return false;
    }
    return Boolean(el.closest(EDITABLE_SELECTOR));
}

function isHintVisible(el) {
    if (!el || el.disabled || el.getAttribute("aria-disabled") === "true") {
        return false;
    }
    if (el.classList.contains("d-none") || el.hasAttribute("disabled")) {
        return false;
    }
    const style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") {
        return false;
    }
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
}

function findHintElement(key) {
    const needle = String(key || "").toUpperCase();
    if (!needle) {
        return null;
    }
    const candidates = document.querySelectorAll(`[data-pba-keyhint="${needle}"]`);
    for (const el of candidates) {
        if (isHintVisible(el)) {
            return el;
        }
    }
    return null;
}

function activateHint(el) {
    if (!el) {
        return false;
    }
    const action = el.dataset.pbaKeyhintAction;
    if (action === "focus") {
        const input = el.matches("input, textarea")
            ? el
            : el.querySelector("input, textarea, [contenteditable='true']");
        (input || el).focus?.();
        if (input?.select) {
            input.select();
        }
        return true;
    }
    el.click();
    return true;
}

patch(Chrome.prototype, {
    setup() {
        super.setup(...arguments);
        this._pbaKeybindingActive = false;
        useExternalListener(window, "keydown", this._pbaOnKeybindingKeyDown, {
            capture: true,
        });
        useExternalListener(window, "keyup", this._pbaOnKeybindingKeyUp, {
            capture: true,
        });
        useExternalListener(window, "blur", this._pbaDeactivateKeybinding);
    },

    _pbaSyncDynamicHints() {
        document.querySelectorAll(".list-plus-btn").forEach((el) => {
            if (!el.getAttribute("data-pba-keyhint")) {
                el.setAttribute("data-pba-keyhint", "N");
            }
        });
    },

    _pbaSetKeybindingActive(active) {
        const next = Boolean(active);
        if (next) {
            this._pbaSyncDynamicHints();
        }
        if (this._pbaKeybindingActive === next) {
            return;
        }
        this._pbaKeybindingActive = next;
        document.body.classList.toggle("pba_pos_keybinding_active", next);
    },

    _pbaDeactivateKeybinding() {
        this._pbaSetKeybindingActive(false);
    },

    _pbaOnKeybindingKeyDown(ev) {
        if (ev.key === "Shift") {
            if (!ev.repeat && !isEditableElement(ev.target)) {
                this._pbaSetKeybindingActive(true);
            }
            return;
        }

        if (ev.key.startsWith("F") && /^F([1-9]|1[0-2])$/.test(ev.key)) {
            ev.preventDefault();
            return;
        }

        if (!this._pbaKeybindingActive || !ev.shiftKey) {
            return;
        }

        if (ev.key === "Escape") {
            ev.preventDefault();
            this._pbaDeactivateKeybinding();
            return;
        }

        if (isEditableElement(ev.target)) {
            this._pbaDeactivateKeybinding();
            return;
        }

        const key = ev.key.length === 1 ? ev.key.toUpperCase() : "";
        if (!key || !/[A-Z0-9]/.test(key)) {
            return;
        }

        const target = findHintElement(key);
        if (!target) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        activateHint(target);
        this._pbaDeactivateKeybinding();
    },

    _pbaOnKeybindingKeyUp(ev) {
        if (ev.key === "Shift") {
            this._pbaDeactivateKeybinding();
        }
    },
});
