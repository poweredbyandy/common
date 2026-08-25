/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { getDeviceBridgeBrowserKey } from "@device_bridge/js/device_bridge_client_key";
import {
    getLocalGateway,
    listLocalGateways,
    setLocalGateway,
    setLocalProxy,
} from "@device_bridge/js/device_bridge_local_registry";
import {
    DeviceBridgeWebUsbTransport,
    sanitizeUsbString,
} from "@device_bridge/js/device_bridge_webusb_transport";

const HEARTBEAT_MS = 30000;
let heartbeatTimer = null;

export function formatDeviceBridgeError(error) {
    if (!error) {
        return _t("Unknown device bridge error.");
    }
    if (error.message === "WEBUSB_NOT_AVAILABLE") {
        return _t("WebUSB is not available (use Chrome/Edge over HTTPS).");
    }
    if (error.message === "USB_OPEN_ACCESS_DENIED") {
        return _t(
            "USB permission denied. Close other tabs/apps using the device or assign WinUSB with Zadig on Windows."
        );
    }
    if (error.message === "USB_NO_OUT_ENDPOINT") {
        return _t("No compatible USB OUT endpoint was found.");
    }
    if (error.message === "DEVICE_BRIDGE_NOT_CONFIGURED") {
        return _t("Device is not configured in Odoo.");
    }
    if (error.message === "DEVICE_BRIDGE_NO_GATEWAY") {
        return _t(
            "No online gateway found. Keep a browser connected to the physical device."
        );
    }
    if (error.message === "WEBUSB_DEVICE_NOT_AVAILABLE") {
        return _t(
            "USB printer not available in this browser. Connect it once or keep a gateway online."
        );
    }
    if (error.name === "NotFoundError") {
        return _t("No device was selected.");
    }
    return error.message || String(error);
}

async function callModel(model, method, args = [], kwargs = {}) {
    return rpc(`/web/dataset/call_kw/${model}/${method}`, {
        model,
        method,
        args,
        kwargs,
    });
}

function bytesToBase64(uint8Array) {
    let binary = "";
    const chunkSize = 0x8000;
    for (let i = 0; i < uint8Array.length; i += chunkSize) {
        binary += String.fromCharCode(...uint8Array.subarray(i, i + chunkSize));
    }
    return btoa(binary);
}

async function heartbeatAllGateways() {
    for (const [deviceCode, gateway] of listLocalGateways()) {
        try {
            const updated = await callModel("device.bridge.gateway", "heartbeat", [
                gateway.id,
                getDeviceBridgeBrowserKey(),
                gateway.channel_token,
            ]);
            setLocalGateway(deviceCode, updated);
        } catch {
            setLocalGateway(deviceCode, null);
        }
    }
    if (!listLocalGateways().length && heartbeatTimer) {
        clearInterval(heartbeatTimer);
        heartbeatTimer = null;
    }
}

function ensureHeartbeat() {
    if (heartbeatTimer) {
        return;
    }
    heartbeatTimer = setInterval(() => {
        heartbeatAllGateways();
    }, HEARTBEAT_MS);
}

export class DeviceBridgeProxy {
    constructor(options = {}) {
        this.deviceCode = options.deviceCode || options.printerCode;
        this.defaultFilters = options.filters || [];
        this.transport = new DeviceBridgeWebUsbTransport();
        this.authorizedDeviceId = null;
        this.devicePayload = null;
        this.enableGateway = options.enableGateway !== false;
        this.onLocalConnected = options.onLocalConnected || null;
        this.onLocalDisconnected = options.onLocalDisconnected || null;
    }

    get isConnected() {
        return this.transport.isConnected;
    }

    get deviceLabel() {
        return this.transport.deviceLabel;
    }

    get browserKey() {
        return getDeviceBridgeBrowserKey();
    }

    get device() {
        return this.transport.device;
    }

    get gateway() {
        return getLocalGateway(this.deviceCode);
    }

    async loadDevicePayload() {
        if (this.devicePayload) {
            return this.devicePayload;
        }
        const payload = await callModel("device.bridge", "get_device_payload", [
            this.deviceCode,
        ]);
        if (!payload?.id) {
            throw new Error("DEVICE_BRIDGE_NOT_CONFIGURED");
        }
        this.devicePayload = payload;
        return payload;
    }

    async getFilters({ picker = false } = {}) {
        const payload = await this.loadDevicePayload();
        if (picker) {
            const vendors = new Set();
            const source = payload.filters?.length
                ? payload.filters
                : this.defaultFilters;
            for (const filter of source || []) {
                if (filter?.vendorId != null) {
                    vendors.add(filter.vendorId);
                }
            }
            if (vendors.size) {
                return [...vendors].map((vendorId) => ({ vendorId }));
            }
            return source?.length ? source : [{}];
        }
        return payload.filters?.length ? payload.filters : this.defaultFilters;
    }

    _deviceMatchesAuthorized(device, authorized) {
        if (
            device.vendorId !== authorized.vendor_id ||
            device.productId !== authorized.product_id
        ) {
            return false;
        }
        const authSerial = sanitizeUsbString(authorized.serial_number);
        if (!authSerial) {
            return true;
        }
        return sanitizeUsbString(device.serialNumber) === authSerial;
    }

    _deviceMatchesFilters(device, filters) {
        if (!filters?.length) {
            return true;
        }
        return filters.some((filter) => {
            if (filter.vendorId != null && device.vendorId !== filter.vendorId) {
                return false;
            }
            if (
                filter.productId != null &&
                device.productId !== filter.productId
            ) {
                return false;
            }
            return true;
        });
    }

    async _findAuthorizedBrowserDevice() {
        if (!navigator.usb?.getDevices) {
            return null;
        }
        const browserDevices = await navigator.usb.getDevices();
        if (!browserDevices.length) {
            return null;
        }
        let authorized = [];
        try {
            authorized = await callModel(
                "device.bridge.authorization",
                "get_authorized_devices",
                [this.deviceCode, this.browserKey]
            );
        } catch {
            authorized = [];
        }
        for (const auth of authorized) {
            const match = browserDevices.find((device) =>
                this._deviceMatchesAuthorized(device, auth)
            );
            if (match) {
                return { device: match, authorized: auth };
            }
        }
        // Already granted in the browser: reuse without opening the picker.
        const filters = await this.getFilters();
        const vendorFilters = await this.getFilters({ picker: true });
        const match =
            browserDevices.find((device) =>
                this._deviceMatchesFilters(device, filters)
            ) ||
            browserDevices.find((device) =>
                this._deviceMatchesFilters(device, vendorFilters)
            );
        if (match) {
            return { device: match, authorized: null };
        }
        return null;
    }

    async _authorizeCurrentDevice() {
        if (!this.transport.device) {
            return null;
        }
        const device = this.transport.device;
        const authorized = await callModel(
            "device.bridge.authorization",
            "authorize_device",
            [
                {
                    device_code: this.deviceCode,
                    browser_key: this.browserKey,
                    connection_type: "webusb",
                    vendor_id: device.vendorId,
                    product_id: device.productId,
                    serial_number: sanitizeUsbString(device.serialNumber),
                    product_name: sanitizeUsbString(device.productName),
                    manufacturer_name: sanitizeUsbString(device.manufacturerName),
                },
            ]
        );
        this.authorizedDeviceId = authorized?.id || null;
        return authorized;
    }

    async _registerGateway() {
        if (!this.enableGateway || !this.isConnected) {
            return null;
        }
        setLocalProxy(this.deviceCode, this);
        const register = async () =>
            callModel("device.bridge.gateway", "register_gateway", [
                this.deviceCode,
                this.browserKey,
                this.authorizedDeviceId || false,
                this.deviceLabel || false,
            ]);
        try {
            if (!this.authorizedDeviceId) {
                await this._authorizeCurrentDevice();
            }
            const payload = await register();
            setLocalGateway(this.deviceCode, payload);
            ensureHeartbeat();
            return payload;
        } catch (error) {
            try {
                await this._authorizeCurrentDevice();
                const payload = await register();
                setLocalGateway(this.deviceCode, payload);
                ensureHeartbeat();
                return payload;
            } catch (retryError) {
                console.warn("device_bridge gateway register failed", retryError);
                return null;
            }
        }
    }

    async _unregisterGateway() {
        const gateway = getLocalGateway(this.deviceCode);
        setLocalProxy(this.deviceCode, null);
        setLocalGateway(this.deviceCode, null);
        if (!gateway) {
            return;
        }
        try {
            await callModel("device.bridge.gateway", "unregister_gateway", [
                gateway.id,
                this.browserKey,
                gateway.channel_token,
            ]);
        } catch {
            /* ignore */
        }
    }

    async connect({
        forcePicker = false,
        allowPicker = true,
        shareGateway = true,
        persistDevice = true,
        filters = null,
    } = {}) {
        if (!navigator.usb) {
            throw new Error("WEBUSB_NOT_AVAILABLE");
        }
        if (this.isConnected && !forcePicker) {
            if (persistDevice && shareGateway) {
                await this._registerGateway();
            }
            return this.transport.device;
        }
        await this.disconnect({ keepGateway: persistDevice ? false : true });

        let selected = null;
        if (!forcePicker) {
            selected = await this._findAuthorizedBrowserDevice();
        }
        if (selected?.device) {
            await this.transport.claim(selected.device);
            if (persistDevice) {
                this.authorizedDeviceId = selected.authorized?.id || null;
                if (this.authorizedDeviceId) {
                    await callModel(
                        "device.bridge.authorization",
                        "touch_authorization",
                        [this.authorizedDeviceId, this.browserKey]
                    );
                } else {
                    await this._authorizeCurrentDevice();
                }
                if (shareGateway) {
                    await this._registerGateway();
                }
                if (typeof this.onLocalConnected === "function") {
                    await this.onLocalConnected(this);
                }
            }
            return this.transport.device;
        }

        if (!allowPicker) {
            throw new Error("WEBUSB_DEVICE_NOT_AVAILABLE");
        }

        const pickerFilters =
            filters || (await this.getFilters({ picker: true }));
        const device = await navigator.usb.requestDevice({
            filters: pickerFilters,
        });
        await this.transport.claim(device);
        if (persistDevice) {
            await this._authorizeCurrentDevice();
            if (shareGateway) {
                await this._registerGateway();
            }
            if (typeof this.onLocalConnected === "function") {
                await this.onLocalConnected(this);
            }
        }
        return this.transport.device;
    }

    async disconnect({ keepGateway = false } = {}) {
        const wasConnected = this.isConnected;
        await this.transport.release();
        if (wasConnected && !keepGateway) {
            await this._unregisterGateway();
            if (typeof this.onLocalDisconnected === "function") {
                await this.onLocalDisconnected(this);
            }
        }
    }

    async listOnlineGateways() {
        return callModel("device.bridge.gateway", "get_online_gateways", [
            this.deviceCode,
        ]);
    }

    async ensureOnlineGateway({ allowPicker = false } = {}) {
        if (!this.isConnected) {
            await this.connect({
                forcePicker: false,
                allowPicker,
                shareGateway: true,
            });
            return this.gateway;
        }
        await this._registerGateway();
        return this.gateway;
    }

    async printRemote(uint8Array, options = {}) {
        const data_b64 = bytesToBase64(uint8Array);
        try {
            return await callModel("device.bridge.gateway", "send_raw_job", [
                this.deviceCode,
                data_b64,
                options.gatewayId || false,
            ]);
        } catch (error) {
            const msg = (error?.data?.message || error?.message || "").toLowerCase();
            if (msg.includes("no online gateway")) {
                const err = new Error("DEVICE_BRIDGE_NO_GATEWAY");
                err.cause = error;
                throw err;
            }
            throw error;
        }
    }

    async printLocal(uint8Array, options = {}) {
        const persistDevice = options.persistDevice !== false;
        if (!this.isConnected || options.forcePicker) {
            await this.connect({
                forcePicker: Boolean(options.forcePicker),
                allowPicker: options.allowPicker !== false,
                shareGateway: persistDevice && options.shareGateway !== false,
                persistDevice,
                filters: options.filters || null,
            });
        }
        try {
            await this.transport.transfer(uint8Array);
            if (persistDevice && this.authorizedDeviceId) {
                try {
                    await callModel(
                        "device.bridge.authorization",
                        "touch_authorization",
                        [this.authorizedDeviceId, this.browserKey]
                    );
                } catch {
                    /* ignore */
                }
            }
        } finally {
            if (!persistDevice) {
                await this.disconnect({ keepGateway: true });
            }
        }
    }

    /**
     * @param {Uint8Array} uint8Array
     * @param {{
     *   mode?: 'auto'|'local'|'remote',
     *   forcePicker?: boolean,
     *   allowPicker?: boolean,
     *   persistDevice?: boolean,
     *   filters?: Array,
     *   gatewayId?: number,
     *   shareGateway?: boolean,
     * }} options
     */
    async printRaw(uint8Array, options = {}) {
        if (!uint8Array?.length) {
            throw new Error(_t("There is no data to print."));
        }
        const mode = options.mode || "auto";
        if (mode === "remote") {
            return this.printRemote(uint8Array, options);
        }
        if (mode === "local") {
            return this.printLocal(uint8Array, options);
        }
        let silentError;
        try {
            return await this.printLocal(uint8Array, {
                ...options,
                forcePicker: false,
                allowPicker: false,
                persistDevice: true,
            });
        } catch (error) {
            silentError = error;
        }
        try {
            return await this.printRemote(uint8Array, options);
        } catch (remoteError) {
            if (options.forcePicker === false && options.allowPicker === false) {
                throw silentError || remoteError;
            }
            try {
                return await this.printLocal(uint8Array, {
                    ...options,
                    forcePicker: true,
                    allowPicker: true,
                    persistDevice: false,
                    shareGateway: false,
                    filters: [{}],
                });
            } catch (pickerError) {
                if (remoteError?.message === "DEVICE_BRIDGE_NO_GATEWAY") {
                    throw pickerError;
                }
                throw remoteError;
            }
        }
    }
}
