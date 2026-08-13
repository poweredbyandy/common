/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onWillUnmount } from "@odoo/owl";
import { StockBarcodeKanbanController } from "@stock_barcode/kanban/stock_barcode_kanban_controller";

patch(StockBarcodeKanbanController.prototype, {
    setup() {
        super.setup(...arguments);
        const busService = useService("bus_service");
        let reloadTimeout = null;
        const onAvailable = () => {
            if (reloadTimeout) {
                browser.clearTimeout(reloadTimeout);
            }
            reloadTimeout = browser.setTimeout(() => {
                this.model.load();
            }, 300);
        };
        busService.subscribe("pba.stock.picking/available", onAvailable);
        onWillUnmount(() => {
            busService.unsubscribe("pba.stock.picking/available", onAvailable);
            if (reloadTimeout) {
                browser.clearTimeout(reloadTimeout);
            }
        });
    },
});
