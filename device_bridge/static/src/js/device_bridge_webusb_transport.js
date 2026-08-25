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

export function sanitizeUsbString(value) {
    if (value == null) {
        return "";
    }
    return String(value).replace(/\0/g, "").trim();
}

function collectBulkOutRows(configuration) {
    const rows = [];
    for (const iface of configuration.interfaces) {
        for (const alternate of iface.alternates) {
            const bulkOut = alternate.endpoints.find(
                (endpoint) =>
                    endpoint.type === "bulk" && endpoint.direction === "out"
            );
            if (!bulkOut) {
                continue;
            }
            rows.push({
                interfaceNumber: iface.interfaceNumber,
                bulkOut,
                interfaceClass: alternate.interfaceClass,
            });
        }
    }
    return rows;
}

function rankBulkOutRows(configuration) {
    const rows = collectBulkOutRows(configuration);
    const ranked = rows
        .filter((row) => row.interfaceClass !== 3)
        .map((row) => {
            let score = 0;
            if (row.interfaceClass === 7) {
                score += 100;
            }
            if (row.interfaceClass === 255) {
                score += 80;
            }
            if (row.interfaceNumber === 0) {
                score += 10;
            }
            score -= row.interfaceNumber;
            return { row, score };
        });
    ranked.sort((left, right) => right.score - left.score);
    const preferred = ranked.map((item) => item.row);
    const hidRows = rows.filter((row) => row.interfaceClass === 3);
    return preferred.length ? preferred.concat(hidRows) : rows;
}

export class DeviceBridgeWebUsbTransport {
    constructor() {
        this.device = null;
        this.interfaceNumber = null;
        this.endpointNumber = null;
        this.packetSize = 64;
    }

    get isConnected() {
        return Boolean(this.device?.opened && this.endpointNumber != null);
    }

    get deviceLabel() {
        if (!this.device) {
            return "";
        }
        return (
            sanitizeUsbString(this.device.productName) ||
            sanitizeUsbString(this.device.manufacturerName) ||
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
            const rows = rankBulkOutRows(device.configuration);
            if (!rows.length) {
                throw new Error("USB_NO_OUT_ENDPOINT");
            }
            let lastDenied = null;
            for (const row of rows) {
                try {
                    await device.claimInterface(row.interfaceNumber);
                } catch (error) {
                    if (isUsbAccessDeniedError(error)) {
                        lastDenied = error;
                        continue;
                    }
                    throw error;
                }
                this.device = device;
                this.interfaceNumber = row.interfaceNumber;
                this.endpointNumber = row.bulkOut.endpointNumber;
                this.packetSize = row.bulkOut.packetSize || 64;
                return device;
            }
            if (lastDenied) {
                const err = new Error("USB_OPEN_ACCESS_DENIED");
                err.cause = lastDenied;
                throw err;
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
        this.packetSize = 64;
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
        const packetSize = this.packetSize || 64;
        const chunkSize = Math.min(512, Math.max(packetSize, packetSize * 4));
        for (let offset = 0; offset < uint8Array.length; offset += chunkSize) {
            const chunk = uint8Array.subarray(
                offset,
                Math.min(offset + chunkSize, uint8Array.length)
            );
            const result = await device.transferOut(endpointNumber, chunk);
            if (result.status !== "ok") {
                throw new Error(
                    _t("USB transfer failed (%s).", result.status)
                );
            }
        }
    }
}
