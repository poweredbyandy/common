/** @odoo-module **/

const STORAGE_KEY = "device_bridge.browser_key";
const LEGACY_STORAGE_KEY = "webusb_printer.browser_key";

function createBrowserKey() {
    if (globalThis.crypto?.randomUUID) {
        return globalThis.crypto.randomUUID();
    }
    return `device-bridge-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function getDeviceBridgeBrowserKey() {
    try {
        const existing = globalThis.localStorage?.getItem(STORAGE_KEY);
        if (existing) {
            return existing;
        }
        const legacy = globalThis.localStorage?.getItem(LEGACY_STORAGE_KEY);
        if (legacy) {
            globalThis.localStorage?.setItem(STORAGE_KEY, legacy);
            return legacy;
        }
        const key = createBrowserKey();
        globalThis.localStorage?.setItem(STORAGE_KEY, key);
        return key;
    } catch {
        return createBrowserKey();
    }
}
