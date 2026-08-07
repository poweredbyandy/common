/** @odoo-module */

import { PosData } from "@point_of_sale/app/models/data_service";
import { patch } from "@web/core/utils/patch";

patch(PosData.prototype, {
    sanitizeData() {
        const orders = [...(this.models["pos.order"] || [])];
        for (const order of orders) {
            if (!order.lines) {
                this.localDeleteCascade(order);
                continue;
            }
            if (order.lines.some((line) => line?.is_reward_line && !line.coupon_id)) {
                for (let i = order.lines.length - 1; i >= 0; i--) {
                    order.lines[i].delete();
                }
            }
        }
    },
});
