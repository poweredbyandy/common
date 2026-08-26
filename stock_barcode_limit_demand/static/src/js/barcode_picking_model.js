/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import BarcodePickingModel from "@stock_barcode/models/barcode_picking_model";

patch(BarcodePickingModel.prototype, {
    _blockOverDemand() {
        return Boolean(this.config.barcode_block_over_demand);
    },

    _shouldLimitProductDemand(productId) {
        if (!this._blockOverDemand()) {
            return false;
        }
        const demand = this._getProductDemandQty(productId);
        if (demand > 0) {
            return true;
        }
        return !this.config.barcode_allow_extra_product;
    },

    _getProductDemandQty(productId) {
        let demand = 0;
        for (const moveId of this.record.move_ids || []) {
            const move = this.cache.getRecord("stock.move", moveId);
            if (move?.product_id?.id === productId) {
                demand += move.product_uom_qty || 0;
            }
        }
        return demand;
    },

    _getProductDoneQty(productId) {
        let done = 0;
        for (const line of this.currentState.lines) {
            if (line.product_id?.id === productId) {
                done += this.getQtyDone(line);
            }
        }
        return done;
    },

    _getRemainingProductQty(productId) {
        return this._getProductDemandQty(productId) - this._getProductDoneQty(productId);
    },

    _wouldExceedProductDemand(productId, incrementQty) {
        if (!this._shouldLimitProductDemand(productId)) {
            return false;
        }
        const demand = this._getProductDemandQty(productId);
        return this._getProductDoneQty(productId) + incrementQty > demand + 1e-6;
    },

    _notifyOverDemand(product) {
        const productName = product.display_name || product.name;
        const demand = this._getProductDemandQty(product.id);
        this.trigger("playSound", "error");
        this.notification(
            _t(
                "You cannot scan more than the requested quantity (%(demand)s) for %(product)s.",
                { demand, product: productName }
            ),
            { type: "danger" }
        );
    },

    _shouldCreateLineOnExceed(line) {
        if (this._blockOverDemand()) {
            return false;
        }
        return super._shouldCreateLineOnExceed(...arguments);
    },

    async createNewLine(params) {
        const product =
            params.fieldsParams?.product_id || params.copyOf?.product_id;
        const increment = params.fieldsParams?.qty_done || 1;
        if (product && this._wouldExceedProductDemand(product.id, increment)) {
            this._notifyOverDemand(product);
            return false;
        }
        return super.createNewLine(...arguments);
    },

    _updateLineQty(line, args) {
        if (args.qty_done && line.product_id) {
            const increment = args.qty_done;
            if (this._wouldExceedProductDemand(line.product_id.id, increment)) {
                const remaining = this._getRemainingProductQty(line.product_id.id);
                if (remaining <= 1e-6) {
                    this._notifyOverDemand(line.product_id);
                    return;
                }
                args.qty_done = remaining;
            }
        }
        return super._updateLineQty(...arguments);
    },
});
