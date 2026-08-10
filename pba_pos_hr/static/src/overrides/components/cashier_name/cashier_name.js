/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CashierName } from "@point_of_sale/app/navbar/cashier_name/cashier_name";

patch(CashierName.prototype, {
    async selectCashier(pin = false, login = false, list = false) {
        const employee = await super.selectCashier(pin, login, list);
        if (
            login &&
            employee &&
            this.pos.config.module_pos_hr &&
            this.pos._pbaPosHrNeedsOpening() &&
            employee._role !== "manager"
        ) {
            this.pos.reset_cashier();
            this.pos.hasLoggedIn = false;
            this.pos.showScreen("LoginScreen");
            return false;
        }
        return employee;
    },
});
