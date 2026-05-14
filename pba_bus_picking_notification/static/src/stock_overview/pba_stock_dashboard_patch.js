/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { StockKanbanRenderer } from "@stock/components/stock_overview/stock_overview";
import { onMounted, onWillUnmount } from "@odoo/owl";

patch(StockKanbanRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        let intervalId = null;
        let lastRevision = null;
        onMounted(async () => {
            const hasGroup = await user.hasGroup(
                "pba_bus_picking_notification.group_stock_picking_bus_notify"
            );
            if (!hasGroup) {
                return;
            }
            const poll = async () => {
                try {
                    const rev = await this.orm.call(
                        "stock.picking",
                        "pba_picking_dashboard_revision",
                        []
                    );
                    const key = JSON.stringify(rev);
                    if (lastRevision !== null && lastRevision !== key) {
                        await this.props.list.model.load();
                    }
                    lastRevision = key;
                } catch {
                    return;
                }
            };
            await poll();
            intervalId = browser.setInterval(poll, 10000);
        });
        onWillUnmount(() => {
            if (intervalId) {
                browser.clearInterval(intervalId);
                intervalId = null;
            }
        });
    },
});
