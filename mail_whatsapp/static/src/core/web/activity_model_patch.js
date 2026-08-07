/* @odoo-module */

import { Activity } from "@mail/core/web/activity_model";
import { patch } from "@web/core/utils/patch";

patch(Activity.prototype, {
    /** @type {boolean} */
    is_whatsapp_followup: false,
});
