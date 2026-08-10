/** @odoo-module **/

import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(ProductCard.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
    },

    get showQtyAvailable() {
        return Boolean(
            this.pos?.config?.show_product_qty_available && this.props.product?.is_storable
        );
    },

    get isQtyOffline() {
        return Boolean(this.pos?.data?.network?.offline);
    },

    get orderedQty() {
        const productId = this.props.product?.id;
        if (!productId || !this.pos?.orderedQtyByProductId) {
            return 0;
        }
        return this.pos.orderedQtyByProductId[productId] || 0;
    },

    get availableQty() {
        const base = this.pos?.getProductFreeQty?.(this.props.product) ?? 0;
        return base - this.orderedQty;
    },

    get availableQtyDisplay() {
        return this.env.utils.formatProductQty(this.availableQty, false);
    },

    get availableQtyLabel() {
        const qty = this.availableQtyDisplay;
        if (this.isQtyOffline) {
            return _t("Available (cached): %s", qty);
        }
        return _t("Available: %s", qty);
    },

    get qtyAvailableClass() {
        const qty = this.availableQty;
        let level = "ok";
        if (qty <= 0) {
            level = "out";
        } else if (qty < 5) {
            level = "low";
        }
        const classes = [`o_pba_pos_qty_badge`, `o_pba_pos_qty_${level}`];
        if (this.isQtyOffline) {
            classes.push("o_pba_pos_qty_offline");
        }
        return classes.join(" ");
    },
});
