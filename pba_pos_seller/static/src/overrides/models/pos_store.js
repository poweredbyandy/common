/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    _pbaGetSellerEmployee() {
        if (!this.config.module_pos_hr) {
            return false;
        }
        const cashier = this.get_cashier();
        if (cashier && cashier.model?.modelName === "hr.employee") {
            return cashier;
        }
        return false;
    },

    _pbaAssignSeller(order) {
        if (!order || order.pba_seller_id) {
            return;
        }
        const seller = this._pbaGetSellerEmployee();
        if (seller) {
            order.update({ pba_seller_id: seller });
        }
    },

    createNewOrder(data = {}) {
        const order = super.createNewOrder(...arguments);
        this._pbaAssignSeller(order);
        return order;
    },

    addLineToCurrentOrder(vals, opt = {}, configure = true) {
        const result = super.addLineToCurrentOrder(...arguments);
        this._pbaAssignSeller(this.get_order());
        return result;
    },

    getReceiptHeaderData(order) {
        const data = super.getReceiptHeaderData(...arguments);
        const sellerName = order?.pba_seller_id?.name;
        if (sellerName) {
            data.seller = _t("Seller: %s", sellerName);
        }
        return data;
    },
});
