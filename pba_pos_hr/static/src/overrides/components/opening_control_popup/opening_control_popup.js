/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { OpeningControlPopup } from "@point_of_sale/app/store/opening_control_popup/opening_control_popup";

patch(OpeningControlPopup.prototype, {
    async confirm() {
        await super.confirm(...arguments);
        const session = this.pos.session;
        if (session && session.state !== "opened") {
            session.update({ state: "opened" });
        }
        this.pos._pbaPosHrOpeningAlertShown = false;
        if (!this.pos.config.module_pos_hr) {
            return;
        }
        this.pos.hasLoggedIn = false;
        await this.pos.showLoginScreen();
    },
});
