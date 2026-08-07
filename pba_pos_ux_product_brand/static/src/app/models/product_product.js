/** @odoo-module **/

import { ProductProduct } from "@point_of_sale/app/models/product_product";
import { patch } from "@web/core/utils/patch";

patch(ProductProduct.prototype, {
    get searchString() {
        const brandName = this.product_brand_id?.name || "";
        return [super.searchString, brandName].filter(Boolean).join(" ");
    },
});
