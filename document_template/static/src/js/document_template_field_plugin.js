/** @odoo-module **/

import { Plugin } from "@html_editor/plugin";
import { DynamicPlaceholderPlugin } from "@html_editor/others/dynamic_placeholder_plugin";
import { withSequence } from "@html_editor/utils/resource";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

/**
 * Puts "Field" first in the `/` powerbox so users can insert Odoo fields
 * instead of only format/markdown-like commands.
 */
export class DocumentTemplateFieldPlugin extends Plugin {
    static id = "documentTemplateField";
    static dependencies = ["userCommand", "selection"];

    resources = {
        powerbox_categories: withSequence(1, {
            id: "document_fields",
            name: _t("Fields"),
        }),
        powerbox_items: {
            categoryId: "document_fields",
            commandId: "insertDocumentField",
        },
        user_commands: {
            id: "insertDocumentField",
            title: _t("Field"),
            description: _t("Insert a field from the selected model"),
            keywords: [
                "field",
                "campo",
                "placeholder",
                "variable",
                "dato",
                "merge",
                "object",
            ],
            icon: "fa-hashtag",
            run: this.insertField.bind(this),
        },
    };

    insertField() {
        return this.dependencies.userCommand
            .getCommand("openDynamicPlaceholder")
            .run();
    }
}

/**
 * Keep the caret where the user clicked (e.g. empty table cell) while the
 * field picker popover steals focus.
 */
patch(DynamicPlaceholderPlugin.prototype, {
    open(resModel) {
        const inDocumentTemplate = Boolean(
            this.editable?.closest(".o_document_template_editor")
        );
        if (inDocumentTemplate) {
            this._documentTemplateCursor =
                this.dependencies.selection.preserveSelection();
        } else {
            this._documentTemplateCursor = null;
        }
        return super.open(...arguments);
    },

    onValidate(chain, defaultValue) {
        if (this._documentTemplateCursor) {
            this._documentTemplateCursor.restore();
            this._documentTemplateCursor = null;
        }
        return super.onValidate(...arguments);
    },

    onClose() {
        this._documentTemplateCursor = null;
        return super.onClose(...arguments);
    },
});
