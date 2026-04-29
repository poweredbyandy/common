/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { user } from "@web/core/user";
import { sprintf } from "@web/core/utils/strings";

const USB_CHUNK = 16384;

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

function getEscposReportUrl(action, userContext) {
    let url = `/report/escpos/${action.report_name}`;
    const actionContext = action.context || {};
    if (action.data && JSON.stringify(action.data) !== "{}") {
        const options = encodeURIComponent(JSON.stringify(action.data));
        const context = encodeURIComponent(JSON.stringify(actionContext));
        url += `?options=${options}&context=${context}`;
    } else {
        if (actionContext.active_ids) {
            url += `/${actionContext.active_ids.join(",")}`;
        }
        const context = encodeURIComponent(JSON.stringify(userContext));
        url += `?context=${context}`;
    }
    return url;
}

function buildUsbRequestOptions(action) {
    const vid = Number(action.escpos_usb_vendor_id) || 0;
    const pid = Number(action.escpos_usb_product_id) || 0;
    if (vid > 0) {
        const filter = { vendorId: vid };
        if (pid > 0) {
            filter.productId = pid;
        }
        return { filters: [filter] };
    }
    return { acceptAllDevices: true, filters: [] };
}

async function sendEscposWebUSB(uint8Array, requestOptions) {
    if (!navigator.usb) {
        throw new Error("WebUSB no está disponible en este navegador.");
    }
    const device = await navigator.usb.requestDevice(requestOptions);
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
        for (const iface of configuration.interfaces) {
            const alternate = iface.alternates[0];
            if (!alternate) {
                continue;
            }
            const bulkOut = alternate.endpoints.find(
                (e) => e.type === "bulk" && e.direction === "out"
            );
            if (!bulkOut) {
                continue;
            }
            try {
                await device.claimInterface(iface.interfaceNumber);
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
                await device.releaseInterface(iface.interfaceNumber);
            }
            return;
        }
        throw new Error(
            "No se encontró un endpoint bulk de salida. Compruebe el cable o el manual del equipo."
        );
    } finally {
        if (device.opened) {
            await device.close();
        }
    }
}

async function sendEscposWebSerial(uint8Array, baudRate) {
    const port = await navigator.serial.requestPort();
    await port.open({ baudRate });
    const writer = port.writable.getWriter();
    try {
        await writer.write(uint8Array);
    } finally {
        writer.releaseLock();
        await port.close();
    }
}

async function fetchEscposPayload(action, downloadContext) {
    const url = getEscposReportUrl(action, downloadContext);
    const response = await browser.fetch(url, { credentials: "include" });
    if (!response.ok) {
        const errText = await response.text();
        throw new Error(errText || response.statusText);
    }
    const buffer = await response.arrayBuffer();
    return new Uint8Array(buffer);
}

async function escposReportHandler(action, options, env) {
    if (action.report_type !== "qweb-escpos") {
        return false;
    }
    const logOnly = Boolean(action.escpos_log_payload);
    const transport = action.escpos_transport || "webserial";
    if (!logOnly) {
        if (transport === "webserial" && !("serial" in navigator)) {
            env.services.notification.add(
                _t(
                    "WebSerial no está disponible. Use Chrome o Edge en HTTPS o localhost, o cambie el canal a WebUSB."
                ),
                { type: "danger", sticky: true }
            );
            return true;
        }
        if (transport === "webusb" && !navigator.usb) {
            env.services.notification.add(
                _t(
                    "WebUSB no está disponible. Use Chrome o Edge en HTTPS o localhost."
                ),
                { type: "danger", sticky: true }
            );
            return true;
        }
    }
    env.services.ui.block();
    try {
        const downloadContext = { ...user.context };
        if (action.context) {
            Object.assign(downloadContext, action.context);
        }
        const payload = await fetchEscposPayload(action, downloadContext);
        if (logOnly) {
            env.services.notification.add(
                _t(
                    "Salida registrada en el log del servidor. No se envió a la impresora."
                ),
                { type: "success" }
            );
        } else if (transport === "webusb") {
            const usbOpts = buildUsbRequestOptions(action);
            await sendEscposWebUSB(payload, usbOpts);
            env.services.notification.add(
                _t("Enviado a la impresora por WebUSB."),
                { type: "success" }
            );
        } else {
            const baudRate = action.escpos_baud_rate || 9600;
            await sendEscposWebSerial(payload, baudRate);
            env.services.notification.add(
                _t("Enviado a la impresora por puerto serie."),
                { type: "success" }
            );
        }
    } catch (e) {
        if (e && e.name === "NotFoundError") {
            env.services.notification.add(
                _t("Selección cancelada o dispositivo no encontrado."),
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
                    "El sistema denegó el acceso USB (suele pasar si la impresora está instalada como impresora de Windows y el driver usa el dispositivo). Opciones: desinstalar o desactivar esa impresora en el administrador de dispositivos y volver a intentar; usar un driver WinUSB (p. ej. Zadig) solo si sabe lo que hace; o cambiar el informe a canal WebSerial si la impresora expone un puerto COM."
                ),
                { type: "danger", sticky: true }
            );
            console.error(e.cause || e);
        } else if (e && (e.name === "SecurityError" || e.name === "InvalidStateError")) {
            env.services.notification.add(
                _t(
                    "No se pudo usar el USB: el dispositivo puede estar ocupado por otro programa o por el driver de impresión."
                ),
                { type: "danger", sticky: true }
            );
            console.error(e);
        } else {
            console.error(e);
            const msg = e && e.message ? e.message : String(e);
            env.services.notification.add(
                sprintf(_t("Error al imprimir por ESC/POS: %s"), msg),
                { type: "danger" }
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
    .add("report_escpos_webserial_handler", escposReportHandler);
