/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    get pbaPosHrIsBasicCashier() {
        if (!this.config.module_pos_hr) {
            return false;
        }
        const cashier = this.get_cashier();
        return Boolean(cashier && cashier._role !== "manager");
    },

    _pbaPosHrNeedsOpening() {
        return this.session?.state === "opening_control";
    },

    _pbaPosHrIsManagerEmployee(employee) {
        return Boolean(employee && employee._role === "manager");
    },

    _pbaPosHrShowOpeningRequiredAlert() {
        this.dialog.add(AlertDialog, {
            title: _t("Opening required"),
            body: _t(
                "The register has not been opened yet. Only a manager can open the session. Ask a manager to open it before you can enter."
            ),
        });
    },

    _pbaPosHrRejectBasicOpeningLogin(showAlert = true) {
        this.reset_cashier();
        this.hasLoggedIn = false;
        if (showAlert && !this._pbaPosHrOpeningAlertShown) {
            this._pbaPosHrShowOpeningRequiredAlert();
            this._pbaPosHrOpeningAlertShown = true;
        }
    },

    _pbaPosHrKickBasicWithoutOpening() {
        if (!this.config.module_pos_hr || !this._pbaPosHrNeedsOpening()) {
            return false;
        }
        if (this._pbaPosHrIsManagerEmployee(this.get_cashier())) {
            return false;
        }
        this._pbaPosHrRejectBasicOpeningLogin(true);
        this._pbaPosHrOpeningAlertShown = false;
        this.showScreen("LoginScreen");
        return true;
    },

    set_cashier(employee) {
        if (
            this.config.module_pos_hr &&
            employee &&
            this._pbaPosHrNeedsOpening() &&
            !this._pbaPosHrIsManagerEmployee(employee)
        ) {
            this.hasLoggedIn = false;
            this._pbaPosHrOpeningAlertShown = false;
            this._pbaPosHrShowOpeningRequiredAlert();
            this._pbaPosHrOpeningAlertShown = true;
            return;
        }
        return super.set_cashier(...arguments);
    },

    async afterProcessServerData() {
        await super.afterProcessServerData(...arguments);
        if (this.hasLoggedIn) {
            this._pbaPosHrKickBasicWithoutOpening();
        }
    },

    openOpeningControl() {
        if (!this.shouldShowOpeningControl()) {
            return;
        }
        if (this.pbaPosHrIsBasicCashier) {
            this._pbaPosHrKickBasicWithoutOpening();
            return;
        }
        return super.openOpeningControl(...arguments);
    },

    showScreen(name, props) {
        if (name === "PaymentScreen" && this.pbaPosHrIsBasicCashier) {
            return;
        }
        if (
            name !== "LoginScreen" &&
            this.config.module_pos_hr &&
            this._pbaPosHrNeedsOpening() &&
            !this._pbaPosHrIsManagerEmployee(this.get_cashier())
        ) {
            this._pbaPosHrRejectBasicOpeningLogin(true);
            this._pbaPosHrOpeningAlertShown = false;
            return super.showScreen("LoginScreen");
        }
        this._pbaPosHrOpeningAlertShown = false;
        return super.showScreen(...arguments);
    },

    async pay() {
        if (this.pbaPosHrIsBasicCashier) {
            return;
        }
        return await super.pay(...arguments);
    },
});
