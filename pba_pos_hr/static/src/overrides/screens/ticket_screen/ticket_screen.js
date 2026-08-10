/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

patch(TicketScreen.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(() => {
            if (!this.pos.config.module_pos_hr || !this.pos._pbaPosHrNeedsOpening()) {
                return;
            }
            if (this.pos.pbaPosHrIsBasicCashier || !this.pos.get_cashier()) {
                this.pos._pbaPosHrKickBasicWithoutOpening();
                return;
            }
            this.pos.openOpeningControl();
        });
    },

    _getFilterOptions() {
        const options = super._getFilterOptions(...arguments);
        if (!this.pos.pbaPosHrIsBasicCashier) {
            return options;
        }
        const filtered = new Map();
        for (const [key, value] of options) {
            if (key === "PAYMENT" || key === "SYNCED") {
                continue;
            }
            filtered.set(key, value);
        }
        if (this.state.filter === "PAYMENT" || this.state.filter === "SYNCED") {
            this.state.filter = "ACTIVE_ORDERS";
        }
        return filtered;
    },

    async onFilterSelected(selectedFilter) {
        if (
            this.pos.pbaPosHrIsBasicCashier &&
            (selectedFilter === "PAYMENT" || selectedFilter === "SYNCED")
        ) {
            return;
        }
        return super.onFilterSelected(...arguments);
    },
});
