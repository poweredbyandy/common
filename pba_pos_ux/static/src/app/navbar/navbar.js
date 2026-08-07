/** @odoo-module **/

import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
    get showToggleProductView() {
        return this.pos.mainScreen.component === ProductScreen;
    },

    toggleProductView() {
        const nextView = this.pos.productListView === "grid" ? "list" : "grid";
        this.pos.setProductListView(nextView);
    },
});
