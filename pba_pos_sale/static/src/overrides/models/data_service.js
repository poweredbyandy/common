/** @odoo-module */

import { PosData } from "@point_of_sale/app/models/data_service";
import { patch } from "@web/core/utils/patch";
import { RPCError } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

patch(PosData.prototype, {
    async loadInitialData() {
        try {
            const response = await this.orm.call("pos.session", "load_data", [
                odoo.pos_session_id,
                PosData.modelToLoad,
            ]);
            if (!response || typeof response !== "object") {
                throw new Error(
                    _t(
                        "The Point of Sale received an empty response while loading data. Please reload the page."
                    )
                );
            }
            return response;
        } catch (error) {
            let message = _t("An error occurred while loading the Point of Sale: \n");
            if (error instanceof RPCError) {
                message += error.data?.message || error.message || String(error);
            } else {
                message += error?.message || String(error);
            }
            console.error("POS loadInitialData failed", error);
            window.alert(message);
            throw error;
        }
    },

    sanitizeData() {
        const orderModel = this.models["pos.order"];
        if (!orderModel || typeof orderModel.filter !== "function") {
            return;
        }

        const brokenOrders = orderModel.filter((order) => !order.lines);
        for (const order of brokenOrders) {
            this.localDeleteCascade(order);
        }

        return super.sanitizeData(...arguments);
    },
});
