import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(...arguments);
        if (this.pba_partner_shipping_id === undefined) {
            this.pba_partner_shipping_id = vals.pba_partner_shipping_id || false;
        }
    },

    set_partner(partner) {
        super.set_partner(...arguments);
        this.setPbaPartnerShipping(false);
    },

    setShippingDate(shippingDate) {
        const config = this.config_id;
        if (
            !shippingDate &&
            config?.ship_later &&
            config?.pba_ship_later_default &&
            !this.getHasRefundLines?.()
        ) {
            shippingDate = new Date().toISOString().split("T")[0];
        }
        return super.setShippingDate(shippingDate);
    },

    setPbaPartnerShipping(partner) {
        this.assert_editable();
        this.update({ pba_partner_shipping_id: partner || false });
    },

    getPbaPartnerShipping() {
        return this.pba_partner_shipping_id || false;
    },

    isPbaShippingLocal() {
        return !this.pba_partner_shipping_id;
    },
});
