/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { formatDeviceBridgeError } from "@device_bridge/js/device_bridge_proxy";

export const DEVICE_BRIDGE_CANCELLED = "DEVICE_BRIDGE_CANCELLED";

function askPrintOnThisComputer(env) {
    return new Promise((resolve) => {
        let settled = false;
        const finish = (value) => {
            if (!settled) {
                settled = true;
                resolve(value);
            }
        };
        env.services.dialog.add(
            ConfirmationDialog,
            {
                title: _t("Configured printer not found"),
                body: _t(
                    "The configured printer is not online. Do you want to print on this computer?"
                ),
                confirmLabel: _t("Print on this computer"),
                cancelLabel: _t("Cancel"),
                confirm: () => finish(true),
                cancel: () => finish(false),
            },
            { onClose: () => finish(false) }
        );
    });
}

export async function printThroughDeviceBridge(env, deviceCode, bytes, options = {}) {
    try {
        await env.services.device_bridge.printRaw(deviceCode, bytes, {
            mode: "auto",
            allowPicker: false,
            companyId: options.companyId || false,
        });
        return "bridge";
    } catch (error) {
        if (error?.message !== "DEVICE_BRIDGE_NO_GATEWAY") {
            throw error;
        }
        env.services.ui.unblock();
        const useLocal = await askPrintOnThisComputer(env);
        if (!useLocal) {
            const cancelled = new Error(DEVICE_BRIDGE_CANCELLED);
            cancelled.cause = error;
            throw cancelled;
        }
        env.services.ui.block();
        await env.services.device_bridge.printRaw(deviceCode, bytes, {
            mode: "local",
            forcePicker: true,
            allowPicker: true,
            persistDevice: true,
            shareGateway: true,
            companyId: options.companyId || false,
        });
        return "local";
    }
}

export { formatDeviceBridgeError };
