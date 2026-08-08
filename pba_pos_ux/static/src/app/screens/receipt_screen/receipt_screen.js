/** @odoo-module **/

import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";

patch(ReceiptScreen.prototype, {
    orderDone() {
        super.orderDone(...arguments);
        this.pos._pbaSkipLeaveOnTicketScreen = true;
        try {
            this.pos.showScreen("TicketScreen");
        } finally {
            this.pos._pbaSkipLeaveOnTicketScreen = false;
        }
    },
});
