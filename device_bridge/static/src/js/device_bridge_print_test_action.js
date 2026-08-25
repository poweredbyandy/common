/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import {
    formatDeviceBridgeError,
    printThroughDeviceBridge,
} from "@device_bridge/js/device_bridge_print_flow";

function base64ToUint8Array(value) {
    const binary = atob(value || "");
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
        bytes[index] = binary.charCodeAt(index);
    }
    return bytes;
}

async function deviceBridgePrintTestAction(env, action) {
    const deviceCode =
        action.params?.device_code || action.context?.device_code;
    const companyId =
        action.params?.company_id || action.context?.company_id || false;
    if (!deviceCode) {
        env.services.notification.add(_t("Missing printer code for the test print."), {
            type: "danger",
        });
        return;
    }

    const job = await env.services.orm.call(
        "device.bridge",
        "get_test_print_payload",
        [deviceCode, companyId]
    );
    const bytes = base64ToUint8Array(job.data_b64);
    env.services.ui.block();
    try {
        await printThroughDeviceBridge(env, deviceCode, bytes, { companyId });
        env.services.notification.add(
            _t("Test sent to printer %s.", job.name || deviceCode),
            { type: "success" }
        );
    } catch (error) {
        env.services.notification.add(formatDeviceBridgeError(error), {
            title: _t("Could not print test"),
            type: "danger",
            sticky: true,
        });
    } finally {
        env.services.ui.unblock();
    }
}

registry.category("actions").add("device_bridge_print_test", deviceBridgePrintTestAction);
