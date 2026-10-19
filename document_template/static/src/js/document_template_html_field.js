/** @odoo-module **/

import { onMounted, onWillUnmount } from "@odoo/owl";
import { HtmlField, htmlField } from "@html_editor/fields/html_field";
import { registry } from "@web/core/registry";
import { DocumentTemplateColorPlugin } from "./document_template_color_plugin";
import { DocumentTemplateFieldPlugin } from "./document_template_field_plugin";
import { DocumentTemplateFormatPlugin } from "./document_template_format_plugin";
import { DocumentTemplateTablePlugin } from "./document_template_table_plugin";

export class DocumentTemplateHtmlField extends HtmlField {
    static template = "document_template.HtmlField";

    /**
     * Only the body owns the permanent chrome toolbar so it can stay
     * visible under the menubar without depending on focus.
     */
    get usePermanentToolbar() {
        return this.props.name === "body_html";
    }

    setup() {
        super.setup(...arguments);
        this._toolbarRetry = 0;
        this._toolbarObserver = null;
        onMounted(() => {
            if (this.usePermanentToolbar) {
                this._scheduleToolbarAttach();
            }
        });
        onWillUnmount(() => {
            this._stopToolbarWatch();
            if (this._hostedToolbarEl?.isConnected) {
                this._hostedToolbarEl.remove();
            }
            this._hostedToolbarEl = null;
        });
    }

    getConfig() {
        const config = super.getConfig(...arguments);
        config.Plugins = [
            ...config.Plugins,
            DocumentTemplateFieldPlugin,
            DocumentTemplateFormatPlugin,
            DocumentTemplateTablePlugin,
            DocumentTemplateColorPlugin,
        ];
        const modelName = this.props.record.data.model;
        if (modelName) {
            config.dynamicPlaceholderResModel = modelName;
        }
        return config;
    }

    onEditorLoad(editor) {
        super.onEditorLoad(editor);
        if (this.usePermanentToolbar) {
            this._scheduleToolbarAttach();
        }
    }

    _scheduleToolbarAttach() {
        this._toolbarRetry = 0;
        this._stopToolbarWatch();
        const tick = () => {
            if (this.attachToolbarToHost()) {
                this._watchToolbarHost();
                return;
            }
            this._toolbarRetry += 1;
            if (this._toolbarRetry < 60) {
                requestAnimationFrame(tick);
            } else {
                // Last resort: observe DOM until the toolbar appears
                this._watchToolbarHost();
            }
        };
        requestAnimationFrame(tick);
        setTimeout(() => this.attachToolbarToHost(), 0);
        setTimeout(() => this.attachToolbarToHost(), 100);
        setTimeout(() => this.attachToolbarToHost(), 300);
    }

    _watchToolbarHost() {
        if (this._toolbarObserver || !this.usePermanentToolbar) {
            return;
        }
        const wysiwyg = this._getWysiwygRoot();
        const host = this._getToolbarHost();
        const target = wysiwyg || host;
        if (!target) {
            return;
        }
        this._toolbarObserver = new MutationObserver(() => {
            this.attachToolbarToHost();
        });
        this._toolbarObserver.observe(target, { childList: true, subtree: true });
    }

    _stopToolbarWatch() {
        if (this._toolbarObserver) {
            this._toolbarObserver.disconnect();
            this._toolbarObserver = null;
        }
    }

    _getWysiwygRoot() {
        const editable = this.editor?.editable;
        if (editable) {
            return editable.closest(".o-wysiwyg");
        }
        const form = document.querySelector(".o_document_template_form");
        return (
            form?.querySelector(
                ".o_document_template_body_section .o-wysiwyg"
            ) || null
        );
    }

    _getToolbarHost() {
        const fromEditable = this.editor?.editable?.closest(
            ".o_document_template_form, .o_form_view"
        );
        const form =
            fromEditable || document.querySelector(".o_document_template_form");
        return form?.querySelector(".o_document_template_format_toolbar_host") || null;
    }

    _findLocalToolbar() {
        if (
            this._hostedToolbarEl?.isConnected &&
            this._hostedToolbarEl.classList.contains("o_document_template_chrome_toolbar")
        ) {
            return this._hostedToolbarEl;
        }
        const host = this._getToolbarHost();
        const fromHost = host?.querySelector(
            ".o-we-toolbar.o_document_template_chrome_toolbar"
        );
        if (fromHost) {
            return fromHost;
        }
        const wysiwyg = this._getWysiwygRoot();
        return wysiwyg?.querySelector(":scope > .o-we-toolbar") || null;
    }

    /**
     * Move the body toolbar into the chrome host and keep it visible.
     * @returns {boolean} true when the toolbar is in the host
     */
    attachToolbarToHost() {
        if (!this.usePermanentToolbar) {
            return false;
        }
        const host = this._getToolbarHost();
        const toolbar = this._findLocalToolbar();
        if (!host || !toolbar) {
            return false;
        }
        if (toolbar.parentElement !== host) {
            host.appendChild(toolbar);
        }
        this._hostedToolbarEl = toolbar;
        toolbar.classList.add(
            "o_document_template_chrome_toolbar",
            "o_document_template_toolbar_active"
        );
        toolbar.classList.remove("d-none");
        // Ensure any stray toolbars in the host stay out of the way
        for (const el of host.querySelectorAll(".o-we-toolbar")) {
            if (el !== toolbar) {
                el.classList.add("d-none");
                el.classList.remove("o_document_template_toolbar_active");
            }
        }
        return true;
    }
}

export const documentTemplateHtmlField = {
    ...htmlField,
    component: DocumentTemplateHtmlField,
};

registry.category("fields").add("document_html", documentTemplateHtmlField);
