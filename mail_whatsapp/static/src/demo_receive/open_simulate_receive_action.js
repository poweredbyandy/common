/** @odoo-module **/

import { registry } from "@web/core/registry";

function openSimulateReceiveWindow(_env, action) {
    const accountId =
        action.context?.default_wa_account_id ||
        action.params?.wa_account_id ||
        "";
    const query = accountId ? `?wa_account_id=${encodeURIComponent(accountId)}` : "";
    const url = `/mail_whatsapp/demo/simulate_receive${query}`;
    const features = [
        "popup=yes",
        "width=560",
        "height=760",
        "left=120",
        "top=80",
        "resizable=yes",
        "scrollbars=yes",
    ].join(",");
    const popup = window.open(url, "mail_whatsapp_simulate_receive", features);
    if (popup) {
        popup.focus();
    } else {
        // Popup blocked: fall back to a new tab/window without features.
        window.open(url, "_blank", "noopener,noreferrer");
    }
}

registry
    .category("actions")
    .add("mail_whatsapp_open_simulate_receive", openSimulateReceiveWindow);
