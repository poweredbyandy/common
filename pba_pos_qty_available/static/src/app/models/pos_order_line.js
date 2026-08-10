/** @odoo-module **/

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import {
    buildOrderedQtyByProductId,
    canFulfillProductQty,
    getProductFreeQty,
} from "@pba_pos_qty_available/app/utils/free_qty";

function _pbaGetOpenOrders(models) {
    if (!models?.["pos.order"]) {
        return [];
    }
    return models["pos.order"].filter((order) => order.state === "draft");
}

patch(PosOrderline.prototype, {
    set_quantity(quantity, keep_price) {
        const product = this.product_id;
        const config = this.order_id?.config_id;
        if (config?.show_product_qty_available && product?.is_storable) {
            const quant =
                typeof quantity === "number"
                    ? quantity
                    : parseFloat("" + (quantity ? quantity : 0));
            const orderedQty =
                buildOrderedQtyByProductId(_pbaGetOpenOrders(this.models))[product.id] || 0;
            const baseQty = getProductFreeQty(product);
            const currentLineQty = this.get_quantity();
            if (
                !canFulfillProductQty({
                    enabled: true,
                    isStorable: true,
                    baseQty,
                    orderedQty,
                    currentLineQty,
                    requestedQty: quant,
                })
            ) {
                const available = Math.max(
                    0,
                    baseQty - Math.max(0, orderedQty - currentLineQty)
                );
                return {
                    title: _t("Insufficient stock"),
                    body: _t(
                        "Not enough quantity available for %s. Available: %s",
                        product.display_name,
                        available
                    ),
                };
            }
        }
        return super.set_quantity(quantity, keep_price);
    },
});
