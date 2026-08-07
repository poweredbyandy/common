/* @odoo-module */

import { DiscussApp } from "@mail/core/public_web/discuss_app_model";
import { Record } from "@mail/core/common/record";
import { browser } from "@web/core/browser/browser";

import { patch } from "@web/core/utils/patch";

patch(DiscussApp.prototype, {
    setup(env) {
        super.setup(env);
        this.whatsappFocus = Record.attr(false, {
            compute() {
                return (
                    browser.localStorage.getItem(
                        "mail_whatsapp.discuss_whatsapp_focus"
                    ) === "true"
                );
            },
            /** @this {import("models").DiscussApp} */
            onUpdate() {
                if (this.whatsappFocus) {
                    browser.localStorage.setItem(
                        "mail_whatsapp.discuss_whatsapp_focus",
                        "true"
                    );
                } else {
                    browser.localStorage.removeItem(
                        "mail_whatsapp.discuss_whatsapp_focus"
                    );
                }
            },
        });
    },
});
