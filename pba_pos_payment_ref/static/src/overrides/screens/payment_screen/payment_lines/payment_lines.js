import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreenPaymentLines.prototype, {
    onPaymentRefInput(line, event) {
        line.setPaymentRefNo(event.target.value);
    },

    onPaymentRefKeydown(event) {
        event.stopPropagation();
    },
});
