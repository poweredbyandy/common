/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import BarcodePickingModel from "@stock_barcode/models/barcode_picking_model";

patch(BarcodePickingModel.prototype, {
    get printButtons() {
        const buttons = super.printButtons;
        buttons.push({
            name: _t("Print POS-80"),
            class: "o_print_pos80",
            method: "action_print_pos80",
        });
        return buttons;
    },

    async print(action, method) {
        if (method !== "action_print_pos80") {
            return super.print(action, method);
        }
        if (this._pbaPos80Printing) {
            return;
        }
        this._pbaPos80Printing = true;
        try {
            return await super.print(action, method);
        } finally {
            setTimeout(() => {
                this._pbaPos80Printing = false;
            }, 1500);
        }
    },
});
