/* @odoo-module */

import { DiscussApp } from "@mail/core/public_web/discuss_app_model";
import { patch } from "@web/core/utils/patch";

patch(DiscussApp.prototype, {
    setup(env) {
        super.setup(env);
        this.whatsappFocus = false;
    },
});
