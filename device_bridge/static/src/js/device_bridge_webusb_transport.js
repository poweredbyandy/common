/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";

function isUsbAccessDeniedError(error) {
    if (!error) {
        return false;
    }
    const name = error.name || "";
    const msg = (error.message || "").toLowerCase();
    return (
        name === "SecurityError" ||
        name === "NetworkError" ||
        msg.includes("access denied") ||
        msg.includes("failed to execute 'open'") ||
        msg.includes("failed to open") ||
        msg.includes("unable to claim") ||
        msg.includes("insufficient permissions")
    );
}

export class DeviceBridgeWebUsbTransport {
    constructor() {
        this.device = null;
        this.interfaceNumber = null;
        this.endpointNumber = null;
    }

    get isConnected() {
        return Boolean(this.device?.opened && this.endpointNumber != null);
    }

    get deviceLabel() {
        if (!this.device) {
            return "";
        }
        return (
            this.device.productName ||
            this.device.manufacturerName ||
            `USB ${this.device.vendorId}:${this.device.productId}`
        );
    }

    async claim(device) {
        try {
            if (!device.opened) {
                await device.open();
            }
        } catch (error) {
            if (isUsbAccessDeniedError(error)) {
                const err = new Error("USB_OPEN_ACCESS_DENIED");
                err.cause = error;
                throw err;
            }
            throw error;
        }
        try {
            const config =
                device.configuration ||
                device.configurations.find((item) => item.configurationValue === 1) ||
                device.configurations[0];
            if (!config) {
                throw new Error(_t("USB device has no configuration."));
            }
            if (device.configuration === null) {
                await device.selectConfiguration(config.configurationValue);
            }
            for (const iface of device.configuration.interfaces) {
                const alternate = iface.alternates[0];
                if (!alternate) {
                    continue;
                }
                const bulkOut = alternate.endpoints.find(
                    (endpoint) =>
                        endpoint.type === "bulk" && endpoint.direction === "out"
                );
                if (!bulkOut) {
                    continue;
                }
                try {
                    await device.claimInterface(iface.interfaceNumber);
                } catch (error) {
                    if (isUsbAccessDeniedError(error)) {
                        const err = new Error("USB_OPEN_ACCESS_DENIED");
                        err.cause = error;
                        throw err;
                    }
                    throw error;
                }
                this.device = device;
                this.interfaceNumber = iface.interfaceNumber;
                this.endpointNumber = bulkOut.endpointNumber;
                return device;
            }
            throw new Error("USB_NO_OUT_ENDPOINT");
        } catch (error) {
            try {
                if (device.opened) {
                    await device.close();
                }
            } catch {
                /* ignore */
            }
            throw error;
        }
    }

    async release() {
        const device = this.device;
        const interfaceNumber = this.interfaceNumber;
        this.device = null;
        this.interfaceNumber = null;
        this.endpointNumber = null;
        if (!device) {
            return;
        }
        try {
            if (device.opened && interfaceNumber != null) {
                await device.releaseInterface(interfaceNumber);
            }
        } catch {
            /* ignore */
        }
        try {
            if (device.opened) {
                await device.close();
            }
        } catch {
            /* ignore */
        }
    }

    async transfer(uint8Array) {
        if (!this.isConnected) {
            throw new Error(_t("Local USB device is not connected."));
        }
        const device = this.device;
        const endpointNumber = this.endpointNumber;
        const chunkSize = 16384;
        for (let offset = 0; offset < uint8Array.length; offset += chunkSize) {
            const chunk = uint8Array.subarray(
                offset,
                Math.min(offset + chunkSize, uint8Array.length)
            );
            await device.transferOut(endpointNumber, chunk);
        }
    }
}
