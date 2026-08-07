/** @odoo-module **/

import { ProductProduct } from "@point_of_sale/app/models/product_product";
import { patch } from "@web/core/utils/patch";

patch(ProductProduct, {
    extraFields: {
        ...(ProductProduct.extraFields || {}),
        free_qty: {
            model: "product.product",
            name: "free_qty",
            type: "float",
            compute: true,
        },
    },
});
