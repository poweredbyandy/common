/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { getDeviceBridgeBrowserKey } from "@device_bridge/js/device_bridge_client_key";
import { sanitizeUsbString } from "@device_bridge/js/device_bridge_webusb_transport";

function slugifyCode(value) {
    return (value || "")
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "")
        .slice(0, 64);
}

export class DeviceBridgeRegisterAction extends Component {
    static template = "device_bridge.RegisterAction";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            saving: false,
            selecting: false,
            deviceTypes: [],
            protocols: [],
            name: "",
            code: "",
            codeManual: false,
            device_type: "printer",
            protocol: "escpos",
            share_websocket: true,
            usb: null,
            error: "",
        });

        onWillStart(async () => {
            const payload = await this.orm.call(
                "device.bridge",
                "get_register_defaults",
                []
            );
            this.state.deviceTypes = payload.device_types || [];
            this.state.protocols = payload.protocols || [];
            const defaults = payload.defaults || {};
            this.state.device_type = defaults.device_type || "printer";
            this.state.protocol = defaults.protocol || "escpos";
            this.state.share_websocket = defaults.share_websocket !== false;
            this.state.loading = false;
        });
    }

    onNameInput(ev) {
        this.state.name = ev.target.value;
        if (!this.state.codeManual) {
            this.state.code = slugifyCode(this.state.name);
        }
    }

    onCodeInput(ev) {
        this.state.codeManual = true;
        this.state.code = slugifyCode(ev.target.value);
    }

    get usbLabel() {
        const usb = this.state.usb;
        if (!usb) {
            return _t("No USB device selected");
        }
        const name = usb.productName || usb.manufacturerName || _t("USB device");
        const ids = `${usb.vendorId.toString(16).padStart(4, "0")}:${usb.productId
            .toString(16)
            .padStart(4, "0")}`;
        const serial = usb.serialNumber ? ` - ${usb.serialNumber}` : "";
        return `${name} [${ids}]${serial}`;
    }

    async onSelectUsb() {
        this.state.error = "";
        if (!navigator.usb) {
            this.state.error = _t(
                "WebUSB is not available. Use Chrome/Edge over HTTPS or localhost."
            );
            return;
        }
        this.state.selecting = true;
        try {
            const device = await navigator.usb.requestDevice({ filters: [{}] });
            this.state.usb = {
                vendorId: device.vendorId,
                productId: device.productId,
                serialNumber: sanitizeUsbString(device.serialNumber),
                productName: sanitizeUsbString(device.productName),
                manufacturerName: sanitizeUsbString(device.manufacturerName),
            };
            if (!this.state.name) {
                this.state.name =
                    this.state.usb.productName ||
                    this.state.usb.manufacturerName ||
                    _t("USB device");
                if (!this.state.codeManual) {
                    this.state.code = slugifyCode(this.state.name);
                }
            }
        } catch (error) {
            if (error?.name !== "NotFoundError") {
                this.state.error = error.message || String(error);
            }
        } finally {
            this.state.selecting = false;
        }
    }

    async onSave() {
        this.state.error = "";
        if (!this.state.usb) {
            this.state.error = _t("Select a USB device first.");
            return;
        }
        if (!this.state.name.trim()) {
            this.state.error = _t("Device name is required.");
            return;
        }
        this.state.saving = true;
        try {
            const result = await this.orm.call(
                "device.bridge",
                "register_browser_device",
                [
                    {
                        name: this.state.name.trim(),
                        code: this.state.code,
                        device_type: this.state.device_type,
                        protocol: this.state.protocol,
                        share_websocket: this.state.share_websocket,
                        browser_key: getDeviceBridgeBrowserKey(),
                        connection_type: "webusb",
                        vendor_id: this.state.usb.vendorId,
                        product_id: this.state.usb.productId,
                        serial_number: this.state.usb.serialNumber,
                        product_name: this.state.usb.productName,
                        manufacturer_name: this.state.usb.manufacturerName,
                    },
                ]
            );
            this.notification.add(_t("Device registered successfully."), {
                type: "success",
            });
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "device.bridge",
                res_id: result.device_id,
                views: [[false, "form"]],
                target: "current",
            });
        } catch (error) {
            this.state.error =
                error?.data?.message || error?.message || String(error);
        } finally {
            this.state.saving = false;
        }
    }

    onCancel() {
        this.action.doAction({ type: "ir.actions.act_window_close" });
    }
}

registry.category("actions").add("device_bridge_register", DeviceBridgeRegisterAction);
