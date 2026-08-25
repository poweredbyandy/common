/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import {
    base64ToUint8Array,
    formatPos80PrintError,
    printPos80ThroughBridge,
} from "@pba_printer_delivery/js/pba_printer_delivery_print";

async function pbaPrinterDeliveryPrintAction(env, action) {
    const pickingIds = action.params?.picking_ids || [];
    if (!pickingIds.length) {
        env.services.notification.add(_t("There is no picking to print."), {
            type: "warning",
        });
        return;
    }
    const jobs = await env.services.orm.call(
        "stock.picking",
        "get_pos80_print_payload",
        [pickingIds]
    );
    if (!jobs.length) {
        env.services.notification.add(_t("There is no picking to print."), {
            type: "warning",
        });
        return;
    }
    const errors = [];
    let printed = 0;
    for (const job of jobs) {
        env.services.ui.block();
        try {
            await printPos80ThroughBridge(
                env,
                job.device_code,
                base64ToUint8Array(job.data_b64)
            );
            printed += 1;
        } catch (error) {
            errors.push(formatPos80PrintError(error));
        } finally {
            env.services.ui.unblock();
        }
    }
    if (printed) {
        env.services.notification.add(
            printed === 1
                ? _t("Sent to the POS-80.")
                : _t("Sent %s tickets to the POS-80.", printed),
            { type: "success" }
        );
    }
    if (errors.length) {
        env.services.notification.add(errors.join("\n"), {
            title: _t("Could not print"),
            type: "danger",
            sticky: true,
        });
    }
}

registry.category("actions").add("pba_printer_delivery_print", pbaPrinterDeliveryPrintAction);
