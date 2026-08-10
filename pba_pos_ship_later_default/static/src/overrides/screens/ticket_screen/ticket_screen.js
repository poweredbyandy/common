import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    _getEmptyOrder(partner) {
        const order = super._getEmptyOrder(...arguments);
        if (order?.getShippingDate?.()) {
            order.update({ shipping_date: false });
        }
        return order;
    },

    postRefund(destinationOrder) {
        super.postRefund(...arguments);
        if (destinationOrder?.getHasRefundLines?.()) {
            destinationOrder.update({ shipping_date: false });
        }
    },
});
