/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { localization } from "@web/core/l10n/localization";

const DECIMAL_FIELD_SELECTOR = [
    ".o_field_float",
    ".o_field_float_factor",
    ".o_field_monetary",
    ".o_field_percentage",
].join(", ");

function placeCursorBeforeDecimal(input) {
    if (!input || input.type === "number" || input.readOnly || input.disabled) {
        return;
    }
    const decimalPoint = localization.decimalPoint;
    const value = input.value || "";
    const index = value.lastIndexOf(decimalPoint);
    if (index < 0) {
        return;
    }
    try {
        input.setSelectionRange(index, index);
    } catch {
        return;
    }
}

function schedulePlaceCursor(input) {
    const apply = () => {
        if (document.activeElement === input) {
            placeCursorBeforeDecimal(input);
        }
    };
    apply();
    queueMicrotask(apply);
    browser.requestAnimationFrame(apply);
    browser.setTimeout(apply, 0);
}

function onFocusIn(ev) {
    const input = ev.target;
    if (!(input instanceof HTMLInputElement)) {
        return;
    }
    if (!input.closest(DECIMAL_FIELD_SELECTOR)) {
        return;
    }
    schedulePlaceCursor(input);
}

browser.addEventListener("focusin", onFocusIn, true);
