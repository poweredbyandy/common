/** @odoo-module **/

import { ImageField } from "@web/views/fields/image/image_field";
import { patch } from "@web/core/utils/patch";
import { onWillUnmount } from "@odoo/owl";

patch(ImageField.prototype, {
    setup() {
        super.setup(...arguments);
        this.state.isExpanded = false;
        this.state.expandedSrc = "";
        this.state.expandedFallbackSrc = "";
        this._pbaOnImageExpandKeydown = (ev) => {
            if (ev.key === "Escape" && this.state.isExpanded) {
                this.onCloseImageExpand();
            }
        };
        window.addEventListener("keydown", this._pbaOnImageExpandKeydown);
        onWillUnmount(() => {
            window.removeEventListener("keydown", this._pbaOnImageExpandKeydown);
            document.body.classList.remove("o_pba_image_expand_no_scroll");
        });
    },

    onImageExpand() {
        if (!this.props.record.data[this.props.name] || !this.state.isValid) {
            return;
        }
        const defaultFieldName =
            this.fieldType === "many2one" ? this.props.previewImage || this.props.name : this.props.name;
        const expandedFieldName = this._getExpandedFieldName(defaultFieldName);
        this.state.expandedSrc = this._getUrlFresh(expandedFieldName);
        this.state.expandedFallbackSrc = this._getUrlFresh(defaultFieldName);
        this.state.isExpanded = true;
        document.body.classList.add("o_pba_image_expand_no_scroll");
    },

    onCloseImageExpand() {
        this.state.isExpanded = false;
        this.state.expandedSrc = "";
        this.state.expandedFallbackSrc = "";
        document.body.classList.remove("o_pba_image_expand_no_scroll");
    },

    onExpandedImageLoadFailed() {
        if (
            this.state.expandedFallbackSrc &&
            this.state.expandedSrc !== this.state.expandedFallbackSrc
        ) {
            this.state.expandedSrc = this.state.expandedFallbackSrc;
        }
    },

    _getExpandedFieldName(defaultFieldName) {
        const highResFieldName = this._toHighResFieldName(defaultFieldName);
        if (!highResFieldName) {
            return defaultFieldName;
        }
        if (this.fieldType === "many2one") {
            return highResFieldName;
        }
        return this.props.record.fields[highResFieldName] ? highResFieldName : defaultFieldName;
    },

    _toHighResFieldName(fieldName) {
        if (!fieldName) {
            return null;
        }
        const match = fieldName.match(/^(.*)_(\d+)$/);
        if (!match) {
            return null;
        }
        const [, baseName, size] = match;
        if (Number(size) >= 1920) {
            return fieldName;
        }
        return `${baseName}_1920`;
    },

    _getUrlFresh(fieldName) {
        const previousLastURL = this.lastURL;
        this.lastURL = undefined;
        const url = this.getUrl(fieldName);
        this.lastURL = previousLastURL;
        return url;
    },

    get imgClass() {
        return `${super.imgClass} o_pba_image_expand_trigger`;
    },
});
