/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { DeviceBridgeProxy } from "@device_bridge/js/device_bridge_proxy";
import {
    getLocalProxy,
    setLocalProxy,
} from "@device_bridge/js/device_bridge_local_registry";

export const deviceBridgeService = {
    dependencies: ["device_bridge_gateway"],

    start() {
        const proxies = new Map();

        function getProxy(deviceCode, options = {}) {
            if (!deviceCode) {
                throw new Error("deviceCode is required");
            }
            let proxy = getLocalProxy(deviceCode) || proxies.get(deviceCode);
            if (!proxy) {
                proxy = new DeviceBridgeProxy({
                    deviceCode,
                    filters: options.filters || [],
                    enableGateway: options.enableGateway !== false,
                });
            }
            proxies.set(deviceCode, proxy);
            setLocalProxy(deviceCode, proxy);
            return proxy;
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
            async listOnlineGateways(deviceCode, options = {}) {
                return getProxy(deviceCode).listOnlineGateways(options.companyId);
            },
        };
    },
};

registry.category("services").add("device_bridge", deviceBridgeService);
