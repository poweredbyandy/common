/** @odoo-module **/

import { registry } from "@web/core/registry";
import {
    POS80_PRINT_NOTIFICATION,
    getDeviceBridge,
    jobDeviceCodes,
    printPos80JobLocal,
} from "@pba_printer_delivery/js/pba_printer_delivery_print";

function hasLocalPrinter(env, payload) {
    const bridge = getDeviceBridge(env);
    if (!bridge?.getProxy) {
        return false;
    }
    return jobDeviceCodes(payload).some((code) => {
        try {
            const proxy = bridge.getProxy(code);
            return Boolean(proxy?.isConnected || proxy?.gateway);
        } catch {
            return false;
        }
    });
}

export const pbaPrinterDeliveryService = {
    dependencies: ["bus_service"],

    async start(env, { bus_service: busService }) {
        busService.subscribe(POS80_PRINT_NOTIFICATION, async (payload) => {
            if (!payload?.data_b64 || !hasLocalPrinter(env, payload)) {
                return;
            }
            try {
                await printPos80JobLocal(env, payload);
            } catch {
                return;
            }
        });
        await busService.start();
        return {};
    },
};

registry.category("services").add("pba_printer_delivery", pbaPrinterDeliveryService);
