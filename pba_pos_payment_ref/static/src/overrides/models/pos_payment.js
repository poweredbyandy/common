import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    setup(vals) {
        super.setup(...arguments);
        this.payment_ref_no = vals.payment_ref_no || "";
    },

    setPaymentRefNo(value) {
        this.pos_order_id?.assert_editable();
        this.update({ payment_ref_no: value || "" });
    },

    getPaymentRefNo() {
        return this.payment_ref_no || "";
    },

    isBankPayment() {
        return this.payment_method_id?.type === "bank";
    },
});
