/** @odoo-module **/

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

/**
 * Popover with details about a dynamic field chip in the document editor.
 */
export class DocumentTemplateFieldInfoPopover extends Component {
    static template = "document_template.FieldInfoPopover";
    static props = {
        label: String,
        expression: String,
        directive: String,
        defaultValue: { type: String, optional: true },
        path: { type: String, optional: true },
        method: { type: String, optional: true },
        close: { type: Function, optional: true },
    };

    get title() {
        return _t("Field");
    }

    get expressionLabel() {
        return _t("Expression");
    }

    get directiveLabel() {
        return _t("Directive");
    }

    get pathLabel() {
        return _t("Path");
    }

    get methodLabel() {
        return _t("Method");
    }

    get defaultLabel() {
        return _t("Default / placeholder");
    }

    get hint() {
        return _t("Rendered from the selected record when you print or preview.");
    }
}
