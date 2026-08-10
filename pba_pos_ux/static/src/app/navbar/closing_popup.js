/** @odoo-module **/

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(ClosePosPopup.prototype, {
    async closeSession() {
        this.ui.block({ message: _t("Closing register...") });
        try {
            return await super.closeSession(...arguments);
        } finally {
            this.ui.unblock();
        }
    },
});
