/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { DeviceBridgeProxy } from "@device_bridge/js/device_bridge_proxy";
import {
    getLocalGateway,
    getLocalProxy,
    listLocalGateways,
    setLocalGateway,
    setLocalProxy,
} from "@device_bridge/js/device_bridge_local_registry";
import { getDeviceBridgeBrowserKey } from "@device_bridge/js/device_bridge_client_key";

const BUS_NOTIFICATION = "device_bridge/print_job";
const PULL_MS = 3000;

function base64ToBytes(data_b64) {
    const binary = atob(data_b64 || "");
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return bytes;
}

async function callModel(model, method, args = []) {
    return rpc(`/web/dataset/call_kw/${model}/${method}`, {
        model,
        method,
        args,
        kwargs: {},
    });
}

export const deviceBridgeGatewayService = {
    dependencies: ["bus_service"],

    start(env, { bus_service: busService }) {
        let pullTimer = null;

        function getOrCreateProxy(deviceCode) {
            let proxy = getLocalProxy(deviceCode);
            if (!proxy) {
                proxy = new DeviceBridgeProxy({ deviceCode });
                setLocalProxy(deviceCode, proxy);
            }
            return proxy;
        }

        async function printJob(deviceCode, gateway, job) {
            const proxy = getOrCreateProxy(deviceCode);
            try {
                const bytes = base64ToBytes(job.data_b64);
                await proxy.printLocal(bytes, {
                    forcePicker: false,
                    allowPicker: false,
                    persistDevice: true,
                    shareGateway: true,
                });
                await callModel("device.bridge.gateway", "ack_print_job", [
                    job.id,
                    gateway.id,
                    getDeviceBridgeBrowserKey(),
                    gateway.channel_token,
                    true,
                    false,
                ]);
            } catch (error) {
                console.warn("device_bridge gateway print failed", error);
                try {
                    await callModel("device.bridge.gateway", "ack_print_job", [
                        job.id,
                        gateway.id,
                        getDeviceBridgeBrowserKey(),
                        gateway.channel_token,
                        false,
                        error?.message || String(error),
                    ]);
                } catch {
                    /* ignore */
                }
            }
        }

        async function restoreGateways() {
            try {
                const gateways = await callModel(
                    "device.bridge.gateway",
                    "get_my_gateways",
                    [getDeviceBridgeBrowserKey()]
                );
                for (const gateway of gateways || []) {
                    if (gateway.device_code) {
                        setLocalGateway(gateway.device_code, gateway);
                    }
                }
            } catch {
                /* ignore */
            }
        }

        async function pullPrintJobs(deviceCode) {
            if (!listLocalGateways().length) {
                await restoreGateways();
            }
            const entries = deviceCode
                ? [[deviceCode, getLocalGateway(deviceCode)]].filter(
                      ([, gateway]) => gateway
                  )
                : listLocalGateways();
            for (const [code, gateway] of entries) {
                let jobs = [];
                try {
                    jobs = await callModel(
                        "device.bridge.gateway",
                        "pull_print_jobs",
                        [
                            gateway.id,
                            getDeviceBridgeBrowserKey(),
                            gateway.channel_token,
                        ]
                    );
                } catch (error) {
                    console.warn("device_bridge pull jobs failed", error);
                    continue;
                }
                for (const job of jobs || []) {
                    await printJob(code, gateway, job);
                }
            }
        }

        function ensurePullTimer() {
            if (pullTimer) {
                return;
            }
            pullTimer = setInterval(() => {
                if (!listLocalGateways().length) {
                    return;
                }
                pullPrintJobs();
            }, PULL_MS);
        }

        async function onPrintJob(payload) {
            ensurePullTimer();
            await pullPrintJobs(payload?.device_code);
        }

        busService.subscribe(BUS_NOTIFICATION, onPrintJob);
        busService.start();
        restoreGateways().then(() => {
            ensurePullTimer();
            pullPrintJobs();
        });

        return {
            getGateway(deviceCode) {
                return getLocalGateway(deviceCode);
            },
            getProxy(deviceCode) {
                return getLocalProxy(deviceCode);
            },
            pullPrintJobs,
        };
    },
};

registry.category("services").add("device_bridge_gateway", deviceBridgeGatewayService);
