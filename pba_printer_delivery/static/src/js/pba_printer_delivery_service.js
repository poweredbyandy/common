/** @odoo-module **/

import { registry } from "@web/core/registry";
import {
    POS80_PRINT_NOTIFICATION,
    getDeviceBridge,
    printPos80JobThroughBridge,
} from "@pba_printer_delivery/js/pba_printer_delivery_print";

export const pbaPrinterDeliveryService = {
    dependencies: ["bus_service"],

    async start(env, { bus_service: busService }) {
        busService.subscribe(POS80_PRINT_NOTIFICATION, async (payload) => {
            if (!payload?.data_b64 || !getDeviceBridge(env)) {
                return;
            }
            try {
                await printPos80JobThroughBridge(env, payload);
            } catch {
                return;
            }
        });
        await busService.start();
        return {};
    },
};

registry.category("services").add("pba_printer_delivery", pbaPrinterDeliveryService);
