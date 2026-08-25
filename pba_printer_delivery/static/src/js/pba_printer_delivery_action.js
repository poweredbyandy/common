/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import {
    formatPos80PrintError,
    printPos80JobThroughBridge,
} from "@pba_printer_delivery/js/pba_printer_delivery_print";

const POS80_REPORT_NAME = "pba_printer_delivery.pos80_ticket_doc";

function getReportActiveIds(action) {
    const context = action.context || {};
    const nestedContext = action.data?.context || {};
    const candidateLists = [
        context.active_ids,
        nestedContext.active_ids,
        action.data?.active_ids,
    ];
    for (const ids of candidateLists) {
        if (Array.isArray(ids) && ids.length) {
            return ids.filter((recordId) => typeof recordId === "number");
        }
    }
    const activeId =
        context.active_id ?? nestedContext.active_id ?? action.data?.active_id;
    if (typeof activeId === "number") {
        return [activeId];
    }
    return [];
}

const inflightPrints = new Map();

function pickingIdsKey(pickingIds) {
    return pickingIds
        .filter((recordId) => typeof recordId === "number")
        .slice()
        .sort((left, right) => left - right)
        .join(",");
}

async function _printPos80PickingIds(env, pickingIds) {
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
            await printPos80JobThroughBridge(env, job);
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

export async function printPos80PickingIds(env, pickingIds) {
    if (!pickingIds.length) {
        env.services.notification.add(_t("There is no picking to print."), {
            type: "warning",
        });
        return;
    }
    const key = pickingIdsKey(pickingIds);
    if (key && inflightPrints.has(key)) {
        return inflightPrints.get(key);
    }
    const pending = _printPos80PickingIds(env, pickingIds).finally(() => {
        if (key) {
            inflightPrints.delete(key);
        }
    });
    if (key) {
        inflightPrints.set(key, pending);
    }
    return pending;
}

async function pbaPrinterDeliveryPrintAction(env, action) {
    await printPos80PickingIds(env, action.params?.picking_ids || []);
}

async function pbaPrinterDeliveryReportHandler(action, options, env) {
    if (action.type !== "ir.actions.report") {
        return false;
    }
    if (action.report_name !== POS80_REPORT_NAME) {
        return false;
    }
    await printPos80PickingIds(env, getReportActiveIds(action));
    options.onClose?.();
    return true;
}

registry.category("actions").add("pba_printer_delivery_print", pbaPrinterDeliveryPrintAction);
registry
    .category("ir.actions.report handlers")
    .add("pba_printer_delivery_report_handler", pbaPrinterDeliveryReportHandler, {
        sequence: 15,
    });
