/** @odoo-module */

import { PosData } from "@point_of_sale/app/models/data_service";
import { patch } from "@web/core/utils/patch";

patch(PosData.prototype, {
    sanitizeData() {
        const orderModel = this.models["pos.order"];
        if (!orderModel || typeof orderModel.filter !== "function") {
            return;
        }

        const brokenOrders = orderModel.filter((order) => !order.lines);
        for (const order of brokenOrders) {
            this.localDeleteCascade(order);
        }

        const rewardOrders = orderModel.filter((order) =>
            (order.lines || []).some((line) => line?.is_reward_line && !line.coupon_id)
        );
        for (const order of rewardOrders) {
            const lines = order.lines || [];
            for (let i = lines.length - 1; i >= 0; i--) {
                lines[i].delete();
            }
        }
    },
});
