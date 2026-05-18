/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useSubEnv } from "@odoo/owl";
import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { ProductCatalogKanbanRecord } from "@product/product_catalog/kanban_record";
import { _t } from "@web/core/l10n/translation";

patch(ProductCatalogKanbanController.prototype, {
    setup() {
        super.setup();
        this.isStandaloneCatalog = Boolean(
            this.props.context.pba_product_catalog_standalone
        );
    },

    async _defineButtonContent() {
        if (this.isStandaloneCatalog) {
            this.buttonString = _t("Cerrar");
            return;
        }
        return super._defineButtonContent(...arguments);
    },

    async backToQuotation() {
        if (this.isStandaloneCatalog) {
            if (this.env.config.breadcrumbs.length > 1) {
                await this.action.restore();
            } else {
                await this.action.doAction({ type: "ir.actions.act_window_close" });
            }
            return;
        }
        return super.backToQuotation(...arguments);
    },
});

patch(ProductCatalogKanbanRecord.prototype, {
    setup() {
        super.setup();
        if (this.props.record.context.pba_product_catalog_standalone) {
            useSubEnv({ pbaProductCatalogStandalone: true });
        }
    },
});
