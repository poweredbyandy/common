/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(ClosePosPopup.prototype, {
    async handleClosingError(response) {
        if (response.pba_needs_seller_session) {
            this.dialog.add(ConfirmationDialog, {
                title: response.title || _t("Error"),
                body: response.message,
                confirmLabel: _t("Review Orders"),
                cancelLabel: _t("Close"),
                confirm: () => {
                    if (!response.redirect) {
                        this.props.close();
                        this.pos.showScreen("TicketScreen");
                    }
                },
                cancel: () => {},
                dismiss: async () => {},
            });
            if (response.redirect) {
                window.location.reload();
            }
            return;
        }
        return super.handleClosingError(...arguments);
    },
});
