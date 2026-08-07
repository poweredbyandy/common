/* @odoo-module */

import { Composer } from "@mail/core/common/composer_model";

Object.assign(Composer.prototype, {
    threadExpired: false,
    whatsappPhone: "",
    whatsappAccountId: false,
    whatsappWindowActive: false,
    whatsappValidUntil: false,
    whatsappTemplates: [],
    whatsappTemplateId: false,
});
