/** @odoo-module **/

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { formatProductDisplayName } from "@pba_pos_ux/utils/product_display_name";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    set_full_product_name() {
        super.set_full_product_name(...arguments);
        this.full_product_name = formatProductDisplayName(
            this.product_id,
            this.full_product_name
        );
    },

    get_full_product_name() {
        return formatProductDisplayName(
            this.product_id,
            super.get_full_product_name(...arguments)
        );
    },

    getDisplayData() {
        const data = super.getDisplayData(...arguments);
        data.productName = formatProductDisplayName(this.product_id, data.productName);
        return data;
    },
});
