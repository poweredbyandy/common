/** @odoo-module */

import { PosData } from "@point_of_sale/app/models/data_service";
import { patch } from "@web/core/utils/patch";

patch(PosData.prototype, {
    sanitizeData() {
        const order_to_delete = this.models["pos.order"].filter((order) =>
            (order.lines || []).some((line) => line.is_reward_line && !line.coupon_id)
        );
        for (const order of order_to_delete) {
            const lines = order.lines || [];
            for (let i = lines.length - 1; i >= 0; i--) {
                lines[i].delete();
            }
        }
    },
});
