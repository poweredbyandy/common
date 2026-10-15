/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { session } from "@web/session";

const NUMERIC_FIELD_SELECTOR = [
    ".o_field_integer",
    ".o_field_float",
    ".o_field_float_factor",
    ".o_field_float_time",
    ".o_field_monetary",
    ".o_field_percentage",
].join(", ");

let mouseFocusedInput = null;

function isEditableNumericInput(target) {
    return (
        target instanceof HTMLInputElement &&
        !target.readOnly &&
        !target.disabled &&
        Boolean(target.closest(NUMERIC_FIELD_SELECTOR))
    );
}

function isFullySelected(input) {
    return input.selectionStart === 0 && input.selectionEnd === input.value.length;
}

function selectAll(input) {
    if (document.activeElement !== input) {
        return;
    }
    try {
        input.select();
    } catch {
        return;
    }
}

function onMouseDown(ev) {
    const input = ev.target;
    mouseFocusedInput =
        isEditableNumericInput(input) && document.activeElement !== input ? input : null;
}

function onMouseUp(ev) {
    const input = mouseFocusedInput;
    mouseFocusedInput = null;
    if (input && ev.target === input && isFullySelected(input)) {
        ev.preventDefault();
    }
}

function onFocusIn(ev) {
    const input = ev.target;
    if (!isEditableNumericInput(input)) {
        return;
    }
    selectAll(input);
    browser.setTimeout(() => selectAll(input), 0);
}

if (session.numeric_focus_select) {
    browser.addEventListener("mousedown", onMouseDown, true);
    browser.addEventListener("mouseup", onMouseUp, true);
    browser.addEventListener("focusin", onFocusIn, true);
}
