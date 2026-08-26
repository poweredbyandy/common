/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import BarcodePickingModel from "@stock_barcode/models/barcode_picking_model";

patch(BarcodePickingModel.prototype, {
    _incrementTrackedLine() {
        if (this.useTrackingNumber) {
            return true;
        }
        return super._incrementTrackedLine(...arguments);
    },

    async createNewLine(params) {
        if (params.fieldsParams) {
            await this._autoAssignLotOnLine(
                params.copyOf || { product_id: params.fieldsParams.product_id },
                params.fieldsParams
            );
        }
        return super.createNewLine(...arguments);
    },

    async updateLine(line, args) {
        await this._autoAssignLotOnLine(line, args);
        return super.updateLine(...arguments);
    },

    lineCanBeEdited(line) {
        if (
            line.product_id?.tracking !== "none" &&
            (line.lot_id || line.lot_name)
        ) {
            return this.lineCanBeSelected(line);
        }
        return super.lineCanBeEdited(...arguments);
    },

    async _autoAssignLotOnLine(line, args) {
        const product = args.product_id || line.product_id;
        if (!product || product.tracking === "none") {
            return;
        }
        if (args.lot_id || args.lot_name || line.lot_id || line.lot_name) {
            return;
        }
        if (!this.record.use_create_lots && !this.record.use_existing_lots) {
            return;
        }
        const lotName = await this.orm.call(
            "stock.picking",
            "get_barcode_next_lot_name",
            [[this.record.id], product.id]
        );
        if (lotName) {
            args.lot_name = lotName;
        }
    },
});
