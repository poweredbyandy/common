/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    shouldShowOpeningControl() {
        if (this.config.pba_seller_pos) {
            return false;
        }
        return super.shouldShowOpeningControl(...arguments);
    },

    async afterProcessServerData() {
        await super.afterProcessServerData(...arguments);
        if (this.config.pba_seller_pos && this.session?.state === "opening_control") {
            await this._pbaSellerPosAutoOpenSession();
        }
    },

    async _pbaSellerPosAutoOpenSession() {
        await this.data.call(
            "pos.session",
            "set_opening_control",
            [this.session.id, 0, false],
            {},
            true
        );
        this.session.state = "opened";
    },

    async closeSession() {
        if (this.config.pba_seller_pos) {
            this.dialog.add(AlertDialog, {
                title: _t("Seller Register"),
                body: _t(
                    "The Seller Register cannot be closed. It must stay open so draft orders can be kept there."
                ),
            });
            return;
        }
        return await super.closeSession(...arguments);
    },
});
