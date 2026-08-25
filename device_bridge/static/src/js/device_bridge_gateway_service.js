/** @odoo-module **/

import { registry } from "@web/core/registry";
import { DeviceBridgeProxy } from "@device_bridge/js/device_bridge_proxy";
import {
    getLocalGateway,
    getLocalProxy,
    setLocalProxy,
} from "@device_bridge/js/device_bridge_local_registry";
import { getDeviceBridgeBrowserKey } from "@device_bridge/js/device_bridge_client_key";

const BUS_NOTIFICATION = "device_bridge/print_job";

function base64ToBytes(data_b64) {
    const binary = atob(data_b64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return bytes;
}

export const deviceBridgeGatewayService = {
    dependencies: ["bus_service"],

    start(env, { bus_service: busService }) {
        async function onPrintJob(payload) {
            if (!payload?.device_code) {
                return;
            }
            const browserKey = getDeviceBridgeBrowserKey();
            if (payload.browser_key !== browserKey) {
                return;
            }
            let proxy = getLocalProxy(payload.device_code);
            if (!proxy) {
                proxy = new DeviceBridgeProxy({
                    deviceCode: payload.device_code,
                });
                setLocalProxy(payload.device_code, proxy);
            }
            const gateway = getLocalGateway(payload.device_code);
            if (
                gateway &&
                (gateway.id !== payload.gateway_id ||
                    gateway.channel_token !== payload.channel_token)
            ) {
                return;
            }
            if (!proxy.isConnected) {
                try {
                    await proxy.connect({
                        forcePicker: false,
                        allowPicker: false,
                        shareGateway: true,
                    });
                } catch (error) {
                    console.warn("device_bridge gateway reconnect failed", error);
                    return;
                }
            }
            try {
                const bytes = base64ToBytes(payload.data_b64);
                await proxy.printLocal(bytes, {
                    shareGateway: true,
                    allowPicker: false,
                    persistDevice: true,
                });
            } catch (error) {
                console.warn("device_bridge gateway print failed", error);
            }
        }

        busService.subscribe(BUS_NOTIFICATION, onPrintJob);
        busService.start();

        return {
            getGateway(deviceCode) {
                return getLocalGateway(deviceCode);
            },
            getProxy(deviceCode) {
                return getLocalProxy(deviceCode);
            },
        };
    },
};

registry.category("services").add("device_bridge_gateway", deviceBridgeGatewayService);
