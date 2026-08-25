/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export const POS80_DEVICE_CODE = "pos80";
export const POS80_PRINT_NOTIFICATION = "pba.stock.picking/print_pos80";
export const POS80_USB_FILTERS = [
    { vendorId: 0x0483 },
    { vendorId: 0x0416 },
    { vendorId: 0x0fe6 },
    { vendorId: 0x1fc9 },
    { vendorId: 0x04b8 },
];

export function base64ToUint8Array(value) {
    const binary = atob(value || "");
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
        bytes[index] = binary.charCodeAt(index);
    }
    return bytes;
}

export function formatPos80PrintError(error) {
    const code = error?.message || "";
    if (code === "DEVICE_BRIDGE_NOT_INSTALLED") {
        return _t("Device Bridge is not installed. Install it to print on the POS-80.");
    }
    if (code === "DEVICE_BRIDGE_NOT_CONFIGURED") {
        return _t("POS-80 is not configured in Device Bridge. Register the printer.");
    }
    if (code === "DEVICE_BRIDGE_NO_GATEWAY") {
        return _t(
            "No online POS-80 gateway. Keep a browser connected to the printer."
        );
    }
    if (code === "WEBUSB_DEVICE_NOT_AVAILABLE") {
        return _t(
            "The POS-80 is not available in this browser. Select it once or keep a gateway online."
        );
    }
    if (code === "WEBUSB_NOT_AVAILABLE") {
        return _t("WebUSB is not available. Use Chrome or Edge over HTTPS.");
    }
    if (code === "USB_OPEN_ACCESS_DENIED") {
        return _t(
            "USB permission denied. Close other tabs using the printer or assign WinUSB with Zadig on Windows."
        );
    }
    if (code === "USB_NO_OUT_ENDPOINT") {
        return _t("No compatible USB OUT endpoint was found on the POS-80.");
    }
    if (error?.name === "NotFoundError") {
        return _t("No printer was selected.");
    }
    return error?.data?.message || error?.message || _t("Could not print on the POS-80.");
}

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
                    "The configured POS-80 is not online. Do you want to print on this computer?"
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

export function getDeviceBridge(env) {
    return env.services.device_bridge || null;
}

export async function printPos80Bytes(env, deviceCode, bytes, options = {}) {
    const bridge = getDeviceBridge(env);
    if (!bridge) {
        throw new Error("DEVICE_BRIDGE_NOT_INSTALLED");
    }
    const code = deviceCode || POS80_DEVICE_CODE;
    await bridge.printRaw(code, bytes, {
        mode: options.mode || "auto",
        allowPicker: options.allowPicker !== false,
        forcePicker: Boolean(options.forcePicker),
        persistDevice: options.persistDevice !== false,
        shareGateway: options.shareGateway !== false,
        filters: POS80_USB_FILTERS,
    });
}

export async function printPos80ThroughBridge(env, deviceCode, bytes) {
    try {
        await printPos80Bytes(env, deviceCode, bytes, {
            mode: "auto",
            allowPicker: false,
        });
        return "bridge";
    } catch (error) {
        if (error?.message !== "DEVICE_BRIDGE_NO_GATEWAY") {
            throw error;
        }
        env.services.ui.unblock();
        const useLocal = await askPrintOnThisComputer(env);
        if (!useLocal) {
            throw error;
        }
        env.services.ui.block();
        await printPos80Bytes(env, deviceCode, bytes, {
            mode: "local",
            forcePicker: true,
            allowPicker: true,
            persistDevice: true,
            shareGateway: true,
        });
        return "local";
    }
}

export function jobDeviceCodes(job) {
    const codes = Array.isArray(job?.device_codes)
        ? job.device_codes.filter(Boolean)
        : [];
    if (codes.length) {
        return codes;
    }
    if (job?.device_code) {
        return [job.device_code];
    }
    return [POS80_DEVICE_CODE];
}

export async function printPos80JobThroughBridge(env, job) {
    const bytes = base64ToUint8Array(job.data_b64);
    let lastError;
    for (const code of jobDeviceCodes(job)) {
        try {
            await printPos80ThroughBridge(env, code, bytes);
            return code;
        } catch (error) {
            lastError = error;
        }
    }
    throw lastError || new Error("DEVICE_BRIDGE_NOT_CONFIGURED");
}

export async function printPos80JobLocal(env, job) {
    const bytes = base64ToUint8Array(job.data_b64);
    let lastError;
    for (const code of jobDeviceCodes(job)) {
        try {
            await printPos80Bytes(env, code, bytes, {
                mode: "local",
                allowPicker: false,
            });
            return code;
        } catch (error) {
            lastError = error;
        }
    }
    throw lastError || new Error("WEBUSB_DEVICE_NOT_AVAILABLE");
}
