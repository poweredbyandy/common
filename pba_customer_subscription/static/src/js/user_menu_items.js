/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

function soporteItem(env) {
    return {
        type: "item",
        id: "pba_soporte",
        description: _t("Soporte"),
        callback: () => {
            env.services.action.doAction("pba_customer_subscription.action_support_dashboard");
        },
        sequence: 20,
    };
}

registry.category("user_menuitems").add("support", soporteItem, { force: true });
