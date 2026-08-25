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
});
