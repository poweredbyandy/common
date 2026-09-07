/** @odoo-module **/

import { ProductCatalogKanbanRecord } from "@product/product_catalog/kanban_record";
import { ProductCatalogOrderLine } from "@product/product_catalog/order_line/order_line";
import { patch } from "@web/core/utils/patch";

if (!ProductCatalogOrderLine.props.pba_qty_mx) {
    ProductCatalogOrderLine.props.pba_qty_mx = { type: Number, optional: true };
}

patch(ProductCatalogKanbanRecord.prototype, {
    setup() {
        super.setup();
        this._ensurePbaQtyMxProp(this.orderLineComponent);
    },

    _ensurePbaQtyMxProp(component) {
        if (component?.props && !component.props.pba_qty_mx) {
            component.props.pba_qty_mx = { type: Number, optional: true };
        }
    },

    _getPbaQtyMx() {
        const multiple = this.productCatalogData?.pba_qty_mx;
        return multiple > 0 ? multiple : 0;
    },

    addProduct(qty = 1) {
        const multiple = this._getPbaQtyMx();
        if (this.productCatalogData.quantity === 0 && multiple) {
            return super.addProduct(multiple);
        }
        return super.addProduct(...arguments);
    },

    increaseQuantity(qty = 1) {
        const multiple = this._getPbaQtyMx();
        return super.increaseQuantity(multiple || qty);
    },

    decreaseQuantity() {
        const multiple = this._getPbaQtyMx();
        if (!multiple) {
            return super.decreaseQuantity();
        }
        const nextQty = this.productCatalogData.quantity - multiple;
        this.updateQuantity(nextQty > 0 ? nextQty : 0);
    },
});
