/** @odoo-module **/

import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import {
    POS80_PRINT_NOTIFICATION,
    base64ToUint8Array,
    getDeviceBridge,
    printPos80Bytes,
} from "@pba_printer_delivery/js/pba_printer_delivery_print";

export const pbaPrinterDeliveryService = {
    dependencies: ["bus_service"],

    async start(env, { bus_service: busService }) {
        const hasGroup = await user.hasGroup(
            "pba_bus_picking_notification.group_stock_picking_bus_notify"
        );
        if (!hasGroup) {
            return {};
        }
        busService.subscribe(POS80_PRINT_NOTIFICATION, async (payload) => {
            if (!payload?.data_b64 || !getDeviceBridge(env)) {
                return;
            }
            try {
                await printPos80Bytes(
                    env,
                    payload.device_code,
                    base64ToUint8Array(payload.data_b64),
                    {
                        mode: "local",
                        allowPicker: false,
                    }
                );
            } catch {
                return;
            }
        });
        await busService.start();
        return {};
    },
};

registry.category("services").add("pba_printer_delivery", pbaPrinterDeliveryService);
