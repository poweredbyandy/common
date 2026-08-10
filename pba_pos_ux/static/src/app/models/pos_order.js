/** @odoo-module **/

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { getValidPosTrackingNumber } from "@pba_pos_ux/utils/order_number";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(...arguments);
        this.tracking_number = getValidPosTrackingNumber({
            trackingNumber: this.tracking_number,
            sequenceNumber: this.sequence_number ?? vals.sequence_number,
            sessionId: this.session_id?.id ?? this.session?.id,
            posReference: this.pos_reference ?? vals.pos_reference ?? vals.name,
        });
    },
});
