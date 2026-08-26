/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import BarcodePickingModel from "@stock_barcode/models/barcode_picking_model";

patch(BarcodePickingModel.prototype, {
    _blockOverDemand() {
        return Boolean(this.config.barcode_block_over_demand);
    },

    _resolveRecordId(record) {
        if (!record) {
            return false;
        }
        return record.id ?? record;
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
        let moveDemand = 0;
        for (const moveId of this.record.move_ids || []) {
            const move = this.cache.getRecord("stock.move", moveId);
            const moveProductId = this._resolveRecordId(move?.product_id);
            if (moveProductId === productId) {
                moveDemand += move.product_uom_qty || 0;
            }
        }
        let reservedDemand = 0;
        for (const line of this.currentState.lines) {
            if (line.product_id?.id === productId) {
                reservedDemand += line.reserved_uom_qty || 0;
            }
        }
        if (this._useReservation && reservedDemand > 0) {
            return Math.max(moveDemand, reservedDemand);
        }
        return moveDemand;
    },

    _getProductDoneQty(productId) {
        let done = 0;
        for (const line of this.currentState.lines) {
            if (line.product_id?.id === productId) {
                done += this.getQtyDone(line) || 0;
            }
        }
        return done;
    },

    _getRemainingProductQty(productId) {
        return this._getProductDemandQty(productId) - this._getProductDoneQty(productId);
    },

    _getRemainingLineQty(line) {
        if (!line?.reserved_uom_qty) {
            return false;
        }
        return line.reserved_uom_qty - (this.getQtyDone(line) || 0);
    },

    _wouldExceedProductDemand(productId, incrementQty, line = null) {
        if (!this._shouldLimitProductDemand(productId)) {
            return false;
        }
        const increment = incrementQty || 0;
        if (line?.reserved_uom_qty > 0) {
            const lineRemaining = this._getRemainingLineQty(line);
            if (lineRemaining > 0 && increment <= lineRemaining + 1e-6) {
                return false;
            }
        }
        const demand = this._getProductDemandQty(productId);
        return this._getProductDoneQty(productId) + increment > demand + 1e-6;
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
        if (
            product &&
            this._wouldExceedProductDemand(product.id, increment, params.copyOf)
        ) {
            this._notifyOverDemand(product);
            return false;
        }
        return super.createNewLine(...arguments);
    },

    async updateLine(line, args) {
        if (args.qty_done && line?.product_id) {
            const increment = args.qty_done;
            if (
                this._wouldExceedProductDemand(
                    line.product_id.id,
                    increment,
                    line
                )
            ) {
                const lineRemaining = this._getRemainingLineQty(line);
                const productRemaining = this._getRemainingProductQty(
                    line.product_id.id
                );
                const remaining = Math.max(
                    lineRemaining || 0,
                    productRemaining
                );
                if (remaining <= 1e-6) {
                    this._notifyOverDemand(line.product_id);
                    return;
                }
                args.qty_done = Math.min(increment, remaining);
            }
        }
        return super.updateLine(...arguments);
    },

    _updateLineQty(line, args) {
        if (args.qty_done && line.product_id) {
            const increment = args.qty_done;
            if (
                this._wouldExceedProductDemand(
                    line.product_id.id,
                    increment,
                    line
                )
            ) {
                const lineRemaining = this._getRemainingLineQty(line);
                const productRemaining = this._getRemainingProductQty(
                    line.product_id.id
                );
                const remaining = Math.max(
                    lineRemaining || 0,
                    productRemaining
                );
                if (remaining <= 1e-6) {
                    this._notifyOverDemand(line.product_id);
                    return;
                }
                args.qty_done = Math.min(increment, remaining);
            }
        }
        return super._updateLineQty(...arguments);
    },
});
