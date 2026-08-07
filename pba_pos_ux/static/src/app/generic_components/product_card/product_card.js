/** @odoo-module **/

import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import {
    formatProductDisplayName,
    getProductDefaultCode,
    stripProductDefaultCodePrefix,
} from "@pba_pos_ux/utils/product_display_name";
import { patch } from "@web/core/utils/patch";

patch(ProductCard.prototype, {
    get isListView() {
        return (this.props.class || "").includes("pba_pos_ux_product_list_item");
    },

    get productReference() {
        return getProductDefaultCode(this.props.product);
    },

    get productCardName() {
        return (
            stripProductDefaultCodePrefix(this.props.name, this.props.product) ||
            this.props.product?.name ||
            this.props.name ||
            ""
        );
    },

    get formattedProductName() {
        return formatProductDisplayName(this.props.product, this.productCardName);
    },

    get displayedProductName() {
        return this.isListView ? this.formattedProductName : this.productCardName;
    },
});
