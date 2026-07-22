/** @odoo-module **/

import { InvoiceButton } from "@point_of_sale/app/screens/ticket_screen/invoice_button/invoice_button";
import { patch } from "@web/core/utils/patch";

patch(InvoiceButton.prototype, {
    async _downloadInvoice() {
        return;
    },
});
