/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { DeviceBridgeProxy } from "@device_bridge/js/device_bridge_proxy";

export const deviceBridgeService = {
    dependencies: ["device_bridge_gateway"],

    start() {
        const proxies = new Map();

        function getProxy(deviceCode, options = {}) {
            if (!deviceCode) {
                throw new Error("deviceCode is required");
            }
            if (!proxies.has(deviceCode)) {
                proxies.set(
                    deviceCode,
                    new DeviceBridgeProxy({
                        deviceCode,
                        filters: options.filters || [],
                        enableGateway: options.enableGateway !== false,
                    })
                );
            }
            return proxies.get(deviceCode);
        }

        async function shareAuthorizedDevices() {
            let codes = [];
            try {
                codes = await rpc(
                    "/web/dataset/call_kw/device.bridge/get_shareable_device_codes",
                    {
                        model: "device.bridge",
                        method: "get_shareable_device_codes",
                        args: [],
                        kwargs: {},
                    }
                );
            } catch {
                return;
            }
            for (const deviceCode of codes || []) {
                try {
                    await getProxy(deviceCode).connect({
                        forcePicker: false,
                        allowPicker: false,
                        persistDevice: true,
                        shareGateway: true,
                    });
                } catch {
                    /* USB not available in this browser */
                }
            }
        }

        shareAuthorizedDevices();

        return {
            getProxy,
            async connect(deviceCode, options = {}) {
                return getProxy(deviceCode, options).connect(options);
            },
            async printRaw(deviceCode, uint8Array, options = {}) {
                return getProxy(deviceCode, options).printRaw(uint8Array, options);
            },
            async listOnlineGateways(deviceCode) {
                return getProxy(deviceCode).listOnlineGateways();
            },
        };
    },
};

registry.category("services").add("device_bridge", deviceBridgeService);
