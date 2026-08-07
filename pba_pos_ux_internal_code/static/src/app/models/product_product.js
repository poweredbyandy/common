/** @odoo-module **/

import { ProductProduct } from "@point_of_sale/app/models/product_product";
import { patch } from "@web/core/utils/patch";

patch(ProductProduct.prototype, {
    get searchString() {
        return [super.searchString, this.internal_code || ""].filter(Boolean).join(" ");
    },
});
