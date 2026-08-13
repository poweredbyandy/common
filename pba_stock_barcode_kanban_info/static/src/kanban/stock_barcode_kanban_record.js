/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { KanbanRecord } from "@web/views/kanban/kanban_record";

const CREDIT_MARK = "\u2060";

patch(KanbanRecord.prototype, {
    getRecordClasses() {
        const classes = super.getRecordClasses(...arguments);
        const record = this.props.record;
        if (!record || record.resModel !== "stock.picking") {
            return classes;
        }
        const data = record.data;
        if (!("pba_barcode_invoice_payment_state" in data)) {
            return classes;
        }
        if (!data.pba_barcode_invoice_payment_state) {
            return classes;
        }
        const term = data.pba_barcode_payment_term_label || "";
        const isCredit = term.startsWith(CREDIT_MARK);
        const isPaid = data.pba_barcode_invoice_payment_state === "paid";
        if (isCredit) {
            return `${classes} o_pba_barcode_tone_credit`;
        }
        if (!isPaid) {
            return `${classes} o_pba_barcode_tone_immediate_unpaid`;
        }
        return classes;
    },
});
