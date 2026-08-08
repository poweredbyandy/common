/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { LoginScreen } from "@point_of_sale/app/screens/login_screen/login_screen";

patch(LoginScreen.prototype, {
    _pbaPosHrShowHomeScreen() {
        if (this.pos.config.module_pos_hr && this.pos.employeeIsAdmin) {
            this.pos.showScreen("TicketScreen");
            this.pos.hasLoggedIn = true;
            return true;
        }
        return false;
    },

    cashierLogIn() {
        if (this._pbaPosHrShowHomeScreen()) {
            return;
        }
        return super.cashierLogIn(...arguments);
    },

    async selectCashier(pin = false, login = false, list = false) {
        const employee = await super.selectCashier(pin, login, list);
        if (login && employee && this._pbaPosHrShowHomeScreen()) {
            return employee;
        }
        return employee;
    },
});
