/** @odoo-module **/

import { registry } from "@web/core/registry";

export const pbaStockBarcodeKanbanService = {
    dependencies: ["bus_service"],

    async start(env, { bus_service: busService }) {
        await busService.start();
        return {};
    },
};

registry.category("services").add("pba_stock_barcode_kanban", pbaStockBarcodeKanbanService);
