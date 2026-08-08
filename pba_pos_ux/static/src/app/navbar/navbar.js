/** @odoo-module **/

import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
    get showToggleProductView() {
        return this.pos.mainScreen.component === ProductScreen;
    },

    get pbaPendingOrderCount() {
        return this.pos.pbaPendingOrderCount || 0;
    },

    getOrderTabs() {
        const current = this.pos.get_order();
        if (!current || current.finalized || current.table_id) {
            return [];
        }
        return [current];
    },

    toggleProductView() {
        const nextView = this.pos.productListView === "grid" ? "list" : "grid";
        this.pos.setProductListView(nextView);
    },
});
