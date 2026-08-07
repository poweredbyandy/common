/** @odoo-module **/

import { ProductProduct } from "@point_of_sale/app/models/product_product";
import { formatProductDisplayName } from "@pba_pos_ux/utils/product_display_name";
import { patch } from "@web/core/utils/patch";

patch(ProductProduct.prototype, {
    get productDisplayName() {
        return formatProductDisplayName(this, this.name);
    },

    get searchString() {
        const fields = ["display_name", "name", "barcode", "default_code"];
        return fields
            .map((field) => this[field] || "")
            .filter(Boolean)
            .join(" ");
    },
});
