/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { getReportUrl } from "@web/webclient/actions/reports/utils";
import { sprintf } from "@web/core/utils/strings";

const USB_CHUNK = 16384;
const ZEBRA_USB_VENDOR_ID = 0x0a5f;

const WEBUSB_LABEL_REPORTS = {
    "stock_picking_epl_webusb.report_picking_epl": "epl",
    "stock_picking_epl_webusb.report_picking_zpl": "zpl",
    "stock_picking_epl_webusb.report_paper_test_epl": "epl",
    "stock_picking_epl_webusb.report_paper_test_zpl": "zpl",
};

function webusbLabelKind(action) {
    return WEBUSB_LABEL_REPORTS[action.report_name] || null;
}

function normalizeEplPayload(raw) {
    let text = raw.replace(/^\uFEFF/, "").replace(/^[\s\x00-\x1f]+/, "");
    const firstN = text.indexOf("N");
    if (firstN > 0) {
        text = text.slice(firstN);
    }
    text = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
    const out = new Uint8Array(text.length);
    for (let i = 0; i < text.length; i++) {
        const c = text.charCodeAt(i);
        out[i] = c <= 255 ? c : 63;
    }
    return out;
}

function normalizeZplPayload(raw) {
    let text = raw.replace(/^\uFEFF/, "").replace(/^[\s\x00-\x1f]+/, "");
    if (!text.startsWith("^")) {
        const xa = text.indexOf("^XA");
        if (xa >= 0) {
            text = text.slice(xa);
        }
    }
    return new TextEncoder().encode(text);
}

function normalizePayload(raw, kind) {
    if (kind === "zpl") {
        return normalizeZplPayload(raw);
    }
    return normalizeEplPayload(raw);
}

function isUsbOpenAccessDeniedError(error) {
    if (!error) {
        return false;
    }
    const name = error.name || "";
    const msg = (error.message || "").toLowerCase();
    return (
        name === "SecurityError" ||
        name === "NetworkError" ||
        msg.includes("access denied") ||
        msg.includes("failed to execute 'open'") ||
        msg.includes("failed to open")
    );
}

function collectBulkOutRows(configuration) {
    const rows = [];
    for (const iface of configuration.interfaces) {
        for (const alternate of iface.alternates) {
            const bulkOut = alternate.endpoints.find(
                (e) => e.type === "bulk" && e.direction === "out"
            );
            if (!bulkOut) {
                continue;
            }
            rows.push({
                interfaceNumber: iface.interfaceNumber,
                bulkOut,
                interfaceClass: alternate.interfaceClass,
            });
        }
    }
    return rows;
}

function pickBulkOutRow(configuration) {
    const rows = collectBulkOutRows(configuration);
    if (!rows.length) {
        return null;
    }
    const iface0 = rows.filter((r) => r.interfaceNumber === 0);
    if (iface0.length === 1) {
        return iface0[0];
    }
    const scored = rows.map((r) => {
        let score = 0;
        if (r.interfaceClass === 255) {
            score += 80;
        }
        if (r.interfaceClass === 7) {
            score += 40;
        }
        score -= r.interfaceNumber * 5;
        score -= r.bulkOut.endpointNumber;
        return { r, score };
    });
    scored.sort((a, b) => b.score - a.score);
    return scored[0].r;
}

async function sendWebUsbBulkOut(uint8Array) {
    if (!navigator.usb) {
        throw new Error("WebUSB no está disponible en este navegador.");
    }
    const device = await navigator.usb.requestDevice({
        filters: [{ vendorId: ZEBRA_USB_VENDOR_ID }],
    });
    try {
        await device.open();
    } catch (e) {
        if (isUsbOpenAccessDeniedError(e)) {
            const err = new Error("USB_OPEN_ACCESS_DENIED");
            err.cause = e;
            throw err;
        }
        throw e;
    }
    try {
        const config =
            device.configuration ||
            device.configurations.find((c) => c.configurationValue === 1) ||
            device.configurations[0];
        if (!config) {
            throw new Error("El dispositivo USB no tiene configuración.");
        }
        if (device.configuration === null) {
            await device.selectConfiguration(config.configurationValue);
        }
        const configuration = device.configuration;
        const row = pickBulkOutRow(configuration);
        if (!row) {
            throw new Error(
                "No se encontró un endpoint bulk de salida en el dispositivo USB."
            );
        }
        const { interfaceNumber, bulkOut } = row;
        try {
            await device.claimInterface(interfaceNumber);
        } catch (e) {
            if (isUsbOpenAccessDeniedError(e)) {
                const err = new Error("USB_CLAIM_ACCESS_DENIED");
                err.cause = e;
                throw err;
            }
            throw e;
        }
        try {
            for (let offset = 0; offset < uint8Array.length; offset += USB_CHUNK) {
                const chunk = uint8Array.subarray(
                    offset,
                    Math.min(offset + USB_CHUNK, uint8Array.length)
                );
                await device.transferOut(bulkOut.endpointNumber, chunk);
            }
        } finally {
            await device.releaseInterface(interfaceNumber);
        }
    } finally {
        if (device.opened) {
            await device.close();
        }
    }
}

async function fetchReportText(action, downloadContext) {
    const mergedContext = { ...downloadContext };
    if (!mergedContext.active_ids?.length && mergedContext.active_id) {
        mergedContext.active_ids = [mergedContext.active_id];
    }
    const actionForUrl = { ...action, context: mergedContext };
    const url = getReportUrl(actionForUrl, "text", mergedContext);
    const response = await browser.fetch(url, { credentials: "include" });
    if (!response.ok) {
        const errText = await response.text();
        throw new Error(errText || response.statusText);
    }
    return await response.text();
}

const EPL_PICKING_BINARY_REPORT =
    "stock_picking_epl_webusb.report_picking_epl";

async function fetchEplPickingBinary(docidsCsv) {
    const url = `/stock_picking_epl_webusb/epl_picking_binary?docids=${encodeURIComponent(
        docidsCsv
    )}`;
    const response = await browser.fetch(url, { credentials: "include" });
    if (!response.ok) {
        const errText = await response.text();
        throw new Error(errText || response.statusText);
    }
    return new Uint8Array(await response.arrayBuffer());
}

async function webusbLabelReportHandler(action, options, env) {
    const kind = webusbLabelKind(action);
    if (action.report_type !== "qweb-text" || !kind) {
        return false;
    }
    if (!navigator.usb) {
        env.services.notification.add(
            _t(
                "WebUSB no está disponible. Use Chrome o Edge en HTTPS o localhost."
            ),
            { type: "danger", sticky: true }
        );
        return true;
    }
    env.services.ui.block();
    try {
        const downloadContext = { ...user.context };
        if (action.context) {
            Object.assign(downloadContext, action.context);
        }
        const mergedContext = { ...downloadContext };
        if (!mergedContext.active_ids?.length && mergedContext.active_id) {
            mergedContext.active_ids = [mergedContext.active_id];
        }
        let payload;
        if (
            kind === "epl" &&
            action.report_name === EPL_PICKING_BINARY_REPORT
        ) {
            const ids = mergedContext.active_ids || [];
            if (!ids.length) {
                throw new Error(_t("No hay albaranes seleccionados."));
            }
            payload = await fetchEplPickingBinary(ids.join(","));
        } else {
            const rawText = await fetchReportText(action, mergedContext);
            payload = normalizePayload(rawText, kind);
        }
        await sendWebUsbBulkOut(payload);
        const msg =
            kind === "zpl"
                ? _t("ZPL enviado a la impresora por WebUSB.")
                : _t("EPL enviado a la impresora por WebUSB.");
        env.services.notification.add(msg, { type: "success" });
    } catch (e) {
        if (e && e.name === "NotFoundError") {
            env.services.notification.add(
                _t("Selección cancelada o impresora no encontrada."),
                { type: "warning" }
            );
        } else if (
            e &&
            (e.message === "USB_OPEN_ACCESS_DENIED" ||
                e.message === "USB_CLAIM_ACCESS_DENIED" ||
                isUsbOpenAccessDeniedError(e))
        ) {
            env.services.notification.add(
                _t(
                    "Acceso USB denegado: si Windows o el driver de la impresora Zebra bloquean el dispositivo, desactive la impresora en «Dispositivos e impresoras» o use un perfil WinUSB solo si conoce el procedimiento."
                ),
                { type: "danger", sticky: true }
            );
            console.error(e.cause || e);
        } else {
            console.error(e);
            const msg = e && e.message ? e.message : String(e);
            env.services.notification.add(
                sprintf(_t("Error al imprimir por WebUSB: %s"), msg),
                { type: "danger", sticky: true }
            );
        }
    } finally {
        env.services.ui.unblock();
    }
    if (action.close_on_report_download) {
        await env.services.action.doAction({ type: "ir.actions.act_window_close" });
    } else if (options.onClose) {
        options.onClose();
    }
    return true;
}

registry
    .category("ir.actions.report handlers")
    .add("stock_picking_epl_webusb_handler", webusbLabelReportHandler);
