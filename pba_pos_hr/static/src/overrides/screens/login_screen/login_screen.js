/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { LoginScreen } from "@point_of_sale/app/screens/login_screen/login_screen";

patch(LoginScreen.prototype, {
    _pbaPosHrShowHomeScreen() {
        const cashier = this.pos.get_cashier();
        if (this.pos.config.module_pos_hr && cashier && cashier._role === "manager") {
            this.pos.hasLoggedIn = true;
            this.pos.showScreen("TicketScreen");
            return true;
        }
        return false;
    },

    cashierLogIn() {
        if (this.pos.config.module_pos_hr && this.pos._pbaPosHrNeedsOpening()) {
            const cashier = this.pos.get_cashier();
            if (!cashier || cashier._role !== "manager") {
                this.pos.reset_cashier();
                this.pos.hasLoggedIn = false;
                return;
            }
        }
        if (this._pbaPosHrShowHomeScreen()) {
            return;
        }
        return super.cashierLogIn(...arguments);
    },

    async selectCashier(pin = false, login = false, list = false) {
        const employee = await super.selectCashier(pin, login, list);
        if (!login || !employee) {
            return employee;
        }
        if (
            this.pos.config.module_pos_hr &&
            this.pos._pbaPosHrNeedsOpening() &&
            employee._role !== "manager"
        ) {
            this.pos.reset_cashier();
            this.pos.hasLoggedIn = false;
            this.pos.showScreen("LoginScreen");
            return false;
        }
        if (this._pbaPosHrShowHomeScreen()) {
            return employee;
        }
        return employee;
    },
});
