import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    createNewOrder(data = {}) {
        const orderData = { ...data };
        if (
            this.config.ship_later &&
            this.config.pba_ship_later_default &&
            !orderData.shipping_date &&
            !orderData.pba_skip_ship_later_default
        ) {
            orderData.shipping_date = new Date().toISOString().split("T")[0];
        }
        delete orderData.pba_skip_ship_later_default;
        return super.createNewOrder(orderData);
    },
});
