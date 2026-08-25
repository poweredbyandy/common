/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import {
    DEVICE_BRIDGE_CANCELLED,
    formatDeviceBridgeError,
    printThroughDeviceBridge,
} from "@device_bridge/js/device_bridge_print_flow";

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

function resolveReportRef(action) {
    if (action.id) {
        return action.id;
    }
    return action.report_name || null;
}

function base64ToUint8Array(value) {
    const binary = atob(value || "");
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
        bytes[index] = binary.charCodeAt(index);
    }
    return bytes;
}

async function deviceBridgeReportActionHandler(action, options, env) {
    if (action.type !== "ir.actions.report") {
        return false;
    }
    const reportRef = resolveReportRef(action);
    if (!reportRef) {
        return false;
    }

    const job = await env.services.orm.call(
        "ir.actions.report",
        "prepare_device_bridge_print",
        [reportRef, getReportActiveIds(action), action.data || {}]
    );
    if (!job?.printers?.length) {
        return false;
    }

    const bytes = base64ToUint8Array(job.data_b64);
    const printedNames = [];
    const errors = [];
    let cancelled = false;
    for (const printer of job.printers) {
        env.services.ui.block();
        try {
            await printThroughDeviceBridge(env, printer.code, bytes, {
                companyId: printer.company_id || job.company_id,
            });
            printedNames.push(printer.name || printer.code);
            break;
        } catch (error) {
            if (error?.message === DEVICE_BRIDGE_CANCELLED) {
                cancelled = true;
                break;
            }
            errors.push(formatDeviceBridgeError(error));
        } finally {
            env.services.ui.unblock();
        }
    }

    if (printedNames.length) {
        const names = printedNames.join(", ");
        env.services.notification.add(
            printedNames.length === 1
                ? _t("Sent to printer %s.", names)
                : _t("Sent to printers: %s", names),
            { type: "success" }
        );
    } else if (errors.length && !cancelled) {
        env.services.notification.add(errors.join("\n"), {
            title: _t("Could not print"),
            type: "danger",
            sticky: true,
        });
    }
    options.onClose?.();
    return true;
}

registry
    .category("ir.actions.report handlers")
    .add("device_bridge_report_action_handler", deviceBridgeReportActionHandler, {
        sequence: 20,
    });
