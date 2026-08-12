/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useSubEnv } from "@odoo/owl";
import { ProductCatalogKanbanRecord } from "@product/product_catalog/kanban_record";
import { ProductCatalogOrderLine } from "@product/product_catalog/order_line/order_line";

patch(ProductCatalogKanbanRecord.prototype, {
    setup() {
        super.setup(...arguments);
        useSubEnv({
            pbaProductCatalogShowPrice:
                this.props.record.context.pba_product_catalog_show_price !== false,
        });
    },
});

patch(ProductCatalogOrderLine.prototype, {
    get showPrice() {
        return super.showPrice && this.env.pbaProductCatalogShowPrice !== false;
    },
});
