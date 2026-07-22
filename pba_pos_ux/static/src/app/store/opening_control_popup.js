/** @odoo-module **/

import { OpeningControlPopup } from "@point_of_sale/app/store/opening_control_popup/opening_control_popup";
import { patch } from "@web/core/utils/patch";

patch(OpeningControlPopup.prototype, {
    async confirm() {
        await super.confirm(...arguments);
        if (this.pos.session.state === "opened") {
            await this.pos._rtPosUxRequestCustomer(this.pos.get_order());
        }
    },
});
