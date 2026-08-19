/** @odoo-module **/

import { Component, onMounted, useEffect, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import qrcode from "./lib/qrcode";

export class QrCodeField extends Component {
    static template = "product_qrcode.QrCodeField";
    static props = { ...standardFieldProps };

    setup() {
        this.state = useState({ imageSrc: "" });
        onMounted(() => this.drawQr());
        useEffect(
            () => {
                this.drawQr();
            },
            () => [this.props.record.data[this.props.name]]
        );
    }

    get value() {
        return this.props.record.data[this.props.name] || "";
    }

    get isUrl() {
        return /^https?:\/\//i.test(this.value);
    }

    drawQr() {
        const value = this.value;
        if (!value) {
            this.state.imageSrc = "";
            return;
        }
        try {
            qrcode.stringToBytes = qrcode.stringToBytesFuncs["UTF-8"];
            const qr = qrcode(0, "M");
            qr.addData(value);
            qr.make();
            const cellSize = 4;
            const count = qr.getModuleCount();
            const canvas = document.createElement("canvas");
            canvas.width = count * cellSize;
            canvas.height = count * cellSize;
            const ctx = canvas.getContext("2d");
            ctx.fillStyle = "#ffffff";
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = "#000000";
            for (let row = 0; row < count; row++) {
                for (let col = 0; col < count; col++) {
                    if (qr.isDark(row, col)) {
                        ctx.fillRect(col * cellSize, row * cellSize, cellSize, cellSize);
                    }
                }
            }
            this.state.imageSrc = canvas.toDataURL("image/png");
        } catch {
            this.state.imageSrc = "";
        }
    }
}

export const qrCodeField = {
    component: QrCodeField,
    displayName: _t("QR Code"),
    supportedTypes: ["char"],
};

registry.category("fields").add("product_qr_code", qrCodeField);
