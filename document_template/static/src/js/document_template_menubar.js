/** @odoo-module **/

import {
    Component,
    useState,
    useRef,
    useEffect,
    onMounted,
    onWillUnmount,
} from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { DocumentTemplatePageSetupDialog } from "./document_template_page_setup_dialog";

export class DocumentTemplateMenubar extends Component {
    static template = "document_template.Menubar";
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.rootRef = useRef("root");
        this.nameInputRef = useRef("nameInput");
        this.mdFileInputRef = useRef("mdFileInput");
        this.docxFileInputRef = useRef("docxFileInput");
        this.state = useState({
            openMenu: null,
            editingName: false,
        });
        this._onDocPointerDown = this._onDocPointerDown.bind(this);
        useEffect(
            () => {
                this.applyEditorMargins();
            },
            () => [
                this.props.record.data.margin_top,
                this.props.record.data.margin_bottom,
                this.props.record.data.margin_left,
                this.props.record.data.margin_right,
                this.props.record.data.header_height,
                this.props.record.data.footer_height,
                this.props.record.data.show_page_numbers,
                this.props.record.data.page_number_format,
                this.props.record.data.page_number_align,
            ]
        );
        onMounted(() => {
            document.addEventListener("pointerdown", this._onDocPointerDown, true);
            this.applyEditorMargins();
        });
        onWillUnmount(() => {
            document.removeEventListener("pointerdown", this._onDocPointerDown, true);
        });
    }

    get documentName() {
        return this.props.record.data.name || "";
    }

    get documentNameLabel() {
        return this.documentName || _t("Untitled document");
    }

    get untitledPlaceholder() {
        return _t("Untitled document");
    }

    applyEditorMargins() {
        const sheet = this.getFormRoot().querySelector(
            ".o_document_template_page_sheet"
        );
        if (!sheet) {
            return;
        }
        const data = this.props.record.data;
        sheet.style.setProperty("--doc-margin-top", `${data.margin_top || 0}mm`);
        sheet.style.setProperty(
            "--doc-margin-bottom",
            `${data.margin_bottom || 0}mm`
        );
        sheet.style.setProperty("--doc-margin-left", `${data.margin_left || 0}mm`);
        sheet.style.setProperty(
            "--doc-margin-right",
            `${data.margin_right || 0}mm`
        );
        sheet.style.setProperty(
            "--doc-header-height",
            `${data.header_height || 20}mm`
        );
        sheet.style.setProperty(
            "--doc-footer-height",
            `${data.footer_height || 15}mm`
        );
        sheet.classList.toggle(
            "o_document_template_show_page_numbers",
            Boolean(data.show_page_numbers)
        );
        sheet.dataset.pageNumberAlign = data.page_number_align || "center";
        sheet.dataset.pageNumberFormat = data.page_number_format || "page_of_total";
        this._syncPageNumberPreview(sheet);
    }

    _syncPageNumberPreview(sheet) {
        const footer = sheet.querySelector(".o_document_template_footer_section");
        if (!footer) {
            return;
        }
        let preview = footer.querySelector(".o_document_template_page_number_preview");
        const show = Boolean(this.props.record.data.show_page_numbers);
        if (!show) {
            if (preview) {
                preview.remove();
            }
            return;
        }
        if (!preview) {
            preview = document.createElement("div");
            preview.className = "o_document_template_page_number_preview";
            footer.appendChild(preview);
        }
        const format = this.props.record.data.page_number_format || "page_of_total";
        const labels = {
            page_of_total: "1 / 3",
            page_of_total_label: "Page 1 of 3",
            page_only: "1",
            page_only_label: "Page 1",
            dash_page: "- 1 -",
        };
        preview.textContent = labels[format] || "1 / 3";
        preview.style.textAlign =
            this.props.record.data.page_number_align || "center";
    }

    get menus() {
        const hasPrint = Boolean(this.props.record.data.has_print_action);
        const useLayout = Boolean(this.props.record.data.use_company_layout);
        return [
            {
                id: "file",
                label: _t("File"),
                items: [
                    {
                        id: "page_setup",
                        label: _t("Page setup…"),
                        action: () => this.openPageSetup(),
                    },
                    { type: "separator" },
                    {
                        id: "preview",
                        label: _t("Preview"),
                        action: () => this.callObject("action_open_preview"),
                        disabled: !this.props.record.resId,
                    },
                    {
                        id: "download_pdf",
                        label: _t("Download PDF"),
                        action: () => this.callObject("action_download_pdf"),
                        disabled: !this.props.record.resId,
                    },
                    {
                        id: "import_markdown",
                        label: _t("Import Markdown…"),
                        action: () => this.openMarkdownImport(),
                    },
                    {
                        id: "import_docx",
                        label: _t("Import Word / Google Docs…"),
                        action: () => this.openDocxImport(),
                    },
                    {
                        id: "add_print",
                        label: _t("Add to Print menu"),
                        action: () => this.callObject("action_add_print"),
                        disabled: !this.props.record.resId || hasPrint,
                        hidden: hasPrint,
                    },
                    {
                        id: "remove_print",
                        label: _t("Remove from Print menu"),
                        action: () => this.callObject("action_remove_print"),
                        disabled: !hasPrint,
                        hidden: !hasPrint,
                    },
                    { type: "separator" },
                    {
                        id: "company_layout",
                        label: useLayout
                            ? _t("Disable company layout")
                            : _t("Enable company layout"),
                        action: () => this.toggleCompanyLayout(),
                    },
                ],
            },
            {
                id: "edit",
                label: _t("Edit"),
                items: [
                    {
                        id: "undo",
                        label: _t("Undo"),
                        shortcut: "Ctrl+Z",
                        action: () => this.dispatchHotkey("z"),
                    },
                    {
                        id: "redo",
                        label: _t("Redo"),
                        shortcut: "Ctrl+Y",
                        action: () => this.dispatchHotkey("y"),
                    },
                    { type: "separator" },
                    {
                        id: "select_all",
                        label: _t("Select all"),
                        shortcut: "Ctrl+A",
                        action: () => this.dispatchHotkey("a"),
                    },
                    {
                        id: "rename",
                        label: _t("Rename"),
                        action: () => this.startRename(),
                    },
                ],
            },
            {
                id: "view",
                label: _t("View"),
                items: [
                    {
                        id: "preview_view",
                        label: _t("Preview"),
                        action: () => this.callObject("action_open_preview"),
                        disabled: !this.props.record.resId,
                    },
                    {
                        id: "page_setup_view",
                        label: _t("Page setup…"),
                        action: () => this.openPageSetup(),
                    },
                ],
            },
            {
                id: "insert",
                label: _t("Insert"),
                items: [
                    {
                        id: "field",
                        label: _t("Field"),
                        action: () => this.insertField(),
                    },
                    {
                        id: "link",
                        label: _t("Link"),
                        action: () => this.clickToolbar("link"),
                    },
                    {
                        id: "image",
                        label: _t("Image"),
                        action: () =>
                            this.clickToolbar("insertMedia") ||
                            this.clickToolbar("media"),
                    },
                ],
            },
            {
                id: "format",
                label: _t("Format"),
                items: [
                    {
                        id: "bold",
                        label: _t("Bold"),
                        shortcut: "Ctrl+B",
                        action: () => this.clickToolbar("bold"),
                    },
                    {
                        id: "italic",
                        label: _t("Italic"),
                        shortcut: "Ctrl+I",
                        action: () => this.clickToolbar("italic"),
                    },
                    {
                        id: "underline",
                        label: _t("Underline"),
                        shortcut: "Ctrl+U",
                        action: () => this.clickToolbar("underline"),
                    },
                    { type: "separator" },
                    {
                        id: "align_left",
                        label: _t("Align left"),
                        action: () => this.clickToolbar("align-left"),
                    },
                    {
                        id: "align_center",
                        label: _t("Align center"),
                        action: () => this.clickToolbar("align-center"),
                    },
                    {
                        id: "align_right",
                        label: _t("Align right"),
                        action: () => this.clickToolbar("align-right"),
                    },
                    {
                        id: "align_justify",
                        label: _t("Justify"),
                        action: () => this.clickToolbar("align-justify"),
                    },
                    { type: "separator" },
                    {
                        id: "bullet",
                        label: _t("Bulleted list"),
                        action: () =>
                            this.clickToolbar("bulleted_list") ||
                            this.clickToolbar("unordered_list"),
                    },
                    {
                        id: "numbered",
                        label: _t("Numbered list"),
                        action: () =>
                            this.clickToolbar("numbered_list") ||
                            this.clickToolbar("ordered_list"),
                    },
                ],
            },
        ];
    }

    async toggleMenu(menuId) {
        if (this.state.openMenu === menuId) {
            this.state.openMenu = null;
            return;
        }
        this.state.editingName = false;
        this.state.openMenu = menuId;
    }

    closeMenus() {
        this.state.openMenu = null;
        this.state.editingName = false;
    }

    _onDocPointerDown(ev) {
        const root = this.rootRef.el;
        if (root && !root.contains(ev.target)) {
            this.closeMenus();
        }
    }

    async onItemClick(item) {
        if (item.disabled || item.type === "separator") {
            return;
        }
        this.closeMenus();
        await item.action();
    }

    openPageSetup() {
        this.closeMenus();
        this.dialog.add(DocumentTemplatePageSetupDialog, {
            record: this.props.record,
            onApplied: async () => {
                this.applyEditorMargins();
            },
        });
    }

    startRename() {
        this.state.openMenu = null;
        this.state.editingName = true;
        requestAnimationFrame(() => {
            const input = this.nameInputRef.el;
            if (input) {
                input.focus();
                input.select();
            }
        });
    }

    onNameClick() {
        this.startRename();
    }

    async onNameChange(ev) {
        if (!this.state.editingName) {
            return;
        }
        const value = ev.target.value.trim();
        this.state.editingName = false;
        const nextName = value || _t("Untitled document");
        if (nextName !== (this.documentName || "")) {
            await this.props.record.update({ name: nextName });
        }
    }

    onNameKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            ev.target.blur();
        } else if (ev.key === "Escape") {
            ev.preventDefault();
            this.state.editingName = false;
        }
    }

    async toggleCompanyLayout() {
        await this.props.record.update({
            use_company_layout: !this.props.record.data.use_company_layout,
        });
    }

    openMarkdownImport() {
        this.closeMenus();
        const input = this.mdFileInputRef.el;
        if (!input) {
            return;
        }
        input.value = "";
        input.click();
    }

    openDocxImport() {
        this.closeMenus();
        const input = this.docxFileInputRef.el;
        if (!input) {
            return;
        }
        input.value = "";
        input.click();
    }

    _suggestNameFromFile(fileName, extensions) {
        const currentName = (this.props.record.data.name || "").trim();
        if (currentName && currentName !== _t("Untitled document")) {
            return null;
        }
        if (!fileName) {
            return null;
        }
        const pattern = new RegExp(`\\.(${extensions})$`, "i");
        return fileName.replace(pattern, "");
    }

    async _applyImportedHtml(html, successMessage, suggestedName) {
        const values = { body_html: html || "" };
        if (suggestedName) {
            values.name = suggestedName;
        }
        await this.props.record.update(values);
        this.notification.add(successMessage, { type: "success" });
    }

    async onMarkdownFileChange(ev) {
        const file = ev.target.files && ev.target.files[0];
        if (!file) {
            return;
        }
        const name = file.name || "";
        if (
            name &&
            !/\.(md|markdown|txt)$/i.test(name) &&
            file.type &&
            !/markdown|text\//.test(file.type)
        ) {
            this.notification.add(_t("Select a Markdown (.md) file."), {
                type: "warning",
            });
            return;
        }
        let text;
        try {
            text = await file.text();
        } catch {
            this.notification.add(_t("Could not read the file."), {
                type: "danger",
            });
            return;
        }
        try {
            const html = await this.orm.call(
                this.props.record.resModel,
                "convert_markdown_to_html",
                [text]
            );
            await this._applyImportedHtml(
                html,
                _t("Markdown converted to rich text."),
                this._suggestNameFromFile(name, "md|markdown|txt")
            );
        } catch (error) {
            this.notification.add(
                error?.data?.message ||
                    error?.message ||
                    _t("Could not convert the Markdown file."),
                { type: "danger" }
            );
        }
    }

    _arrayBufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        const chunk = 0x8000;
        let binary = "";
        for (let i = 0; i < bytes.length; i += chunk) {
            binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
        }
        return btoa(binary);
    }

    async onDocxFileChange(ev) {
        const file = ev.target.files && ev.target.files[0];
        if (!file) {
            return;
        }
        const name = file.name || "";
        if (name && !/\.docx$/i.test(name)) {
            this.notification.add(
                _t("Select a Word / Google Docs (.docx) file."),
                { type: "warning" }
            );
            return;
        }
        let contentB64;
        try {
            const buffer = await file.arrayBuffer();
            contentB64 = this._arrayBufferToBase64(buffer);
        } catch {
            this.notification.add(_t("Could not read the file."), {
                type: "danger",
            });
            return;
        }
        try {
            const html = await this.orm.call(
                this.props.record.resModel,
                "convert_docx_to_html",
                [contentB64]
            );
            await this._applyImportedHtml(
                html,
                _t("Document imported into the body."),
                this._suggestNameFromFile(name, "docx")
            );
        } catch (error) {
            this.notification.add(
                error?.data?.message ||
                    error?.message ||
                    _t("Could not convert the DOCX file."),
                { type: "danger" }
            );
        }
    }

    getFormRoot() {
        return this.rootRef.el?.closest(".o_form_view") || document;
    }

    /**
     * Prefer the editable that currently has the caret (e.g. a table cell in
     * the body), not the first editor on the page (header).
     */
    getEditable() {
        const root = this.getFormRoot();
        const selection =
            root.ownerDocument?.getSelection?.() || document.getSelection();
        const anchor = selection?.anchorNode;
        const fromSelection =
            anchor &&
            (anchor.nodeType === Node.ELEMENT_NODE
                ? anchor
                : anchor.parentElement
            )?.closest?.(
                ".o_document_template_editor [contenteditable='true'], .o_document_template_editor .note-editable"
            );
        if (fromSelection && root.contains(fromSelection)) {
            return fromSelection;
        }
        const active = document.activeElement?.closest?.(
            ".o_document_template_editor [contenteditable='true'], .o_document_template_editor .note-editable"
        );
        if (active && root.contains(active)) {
            return active;
        }
        return (
            root.querySelector(
                ".o_document_template_body_section [contenteditable='true'], .o_document_template_body_section .note-editable"
            ) ||
            root.querySelector(
                ".o_document_template_editor [contenteditable='true'], .o_document_template_editor .note-editable"
            )
        );
    }

    focusEditable() {
        const editable = this.getEditable();
        if (editable) {
            editable.focus();
        }
        return editable;
    }

    dispatchHotkey(key) {
        const editable = this.focusEditable();
        if (!editable) {
            return;
        }
        const eventInit = {
            key: key.toLowerCase(),
            code: `Key${key.toUpperCase()}`,
            keyCode: key.toUpperCase().charCodeAt(0),
            which: key.toUpperCase().charCodeAt(0),
            ctrlKey: true,
            bubbles: true,
            cancelable: true,
        };
        editable.dispatchEvent(new KeyboardEvent("keydown", eventInit));
    }

    clickToolbar(name) {
        const root = this.getFormRoot();
        this.focusEditable();
        const selectors = [
            `.o_document_template_editor .o-we-toolbar button[name="${name}"]`,
            `.o_document_template_editor button[name="${name}"]`,
        ];
        for (const selector of selectors) {
            const button = root.querySelector(selector);
            if (button && !button.disabled) {
                button.click();
                return true;
            }
        }
        if (["bold", "italic", "underline"].includes(name)) {
            return document.execCommand(name);
        }
        return false;
    }

    insertField() {
        if (!this.props.record.data.model) {
            this.notification.add(_t("Select a model first (File → Page setup)."), {
                type: "warning",
            });
            return;
        }
        const root = this.getFormRoot();
        const editable = this.getEditable();
        if (!editable) {
            this.notification.add(
                _t("Click inside the document first."),
                { type: "warning" }
            );
            return;
        }
        editable.focus();
        const wysiwyg = editable.closest(".o-wysiwyg");
        const button =
            (wysiwyg &&
                (wysiwyg.querySelector(
                    'button[name="openDynamicPlaceholder"]'
                ) ||
                    wysiwyg.querySelector(
                        'button[name="insertDocumentField"]'
                    ))) ||
            root.querySelector(
                '.o_document_template_format_toolbar_host button[name="openDynamicPlaceholder"]'
            ) ||
            root.querySelector(
                '.o_document_template_format_toolbar_host button[name="insertDocumentField"]'
            );
        if (button) {
            button.click();
            return;
        }
        document.execCommand("insertText", false, "/");
    }

    async callObject(method) {
        const { record } = this.props;
        if (!record.resId) {
            this.notification.add(_t("Save the template first."), {
                type: "warning",
            });
            return;
        }
        await record.save();
        const result = await this.orm.call(record.resModel, method, [
            [record.resId],
        ]);
        const isAction =
            result &&
            typeof result === "object" &&
            !Array.isArray(result) &&
            typeof result.type === "string";
        if (isAction) {
            await this.action.doAction(result);
        }
        await record.load();
    }
}

export const documentTemplateMenubar = {
    component: DocumentTemplateMenubar,
    fieldDependencies: [
        { name: "name", type: "char" },
        { name: "model", type: "char" },
        { name: "model_id", type: "many2one" },
        { name: "paperformat_id", type: "many2one" },
        { name: "use_company_layout", type: "boolean" },
        { name: "has_print_action", type: "boolean" },
        { name: "body_html", type: "html" },
        { name: "margin_top", type: "float" },
        { name: "margin_bottom", type: "float" },
        { name: "margin_left", type: "float" },
        { name: "margin_right", type: "float" },
        { name: "header_height", type: "float" },
        { name: "footer_height", type: "float" },
        { name: "show_page_numbers", type: "boolean" },
        { name: "page_number_format", type: "selection" },
        { name: "page_number_align", type: "selection" },
    ],
};

registry.category("view_widgets").add("document_template_menubar", documentTemplateMenubar);
