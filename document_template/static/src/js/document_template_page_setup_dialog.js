/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

const MARGIN_PRESETS = {
    normal: { top: 25.4, bottom: 25.4, left: 25.4, right: 25.4 },
    narrow: { top: 12.7, bottom: 12.7, left: 12.7, right: 12.7 },
    moderate: { top: 25.4, bottom: 25.4, left: 19.05, right: 19.05 },
    wide: { top: 25.4, bottom: 25.4, left: 50.8, right: 50.8 },
};

const PAGE_NUMBER_FORMATS = [
    { id: "page_of_total", label: "1 / 3", preview: "1 / 3" },
    { id: "page_of_total_label", label: "Page 1 of 3", preview: "Page 1 of 3" },
    { id: "page_only", label: "1", preview: "1" },
    { id: "page_only_label", label: "Page 1", preview: "Page 1" },
    { id: "dash_page", label: "- 1 -", preview: "- 1 -" },
];

/**
 * Modal to configure model, paper, margins, header/footer and page numbers.
 */
export class DocumentTemplatePageSetupDialog extends Component {
    static template = "document_template.PageSetupDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        record: Object,
        onApplied: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        const data = this.props.record.data;
        this.state = useState({
            modelSearch: "",
            modelOptions: [],
            paperOptions: [],
            loadingModels: false,
            loadingPapers: false,
            modelId: this._m2oId(data.model_id),
            modelName: this._m2oName(data.model_id) || "",
            modelTechnical: data.model || "",
            paperId: this._m2oId(data.paperformat_id),
            paperName: this._m2oName(data.paperformat_id) || "",
            marginPreset: this._detectPreset(data),
            margins: {
                top: Number(data.margin_top) || 0,
                bottom: Number(data.margin_bottom) || 0,
                left: Number(data.margin_left) || 0,
                right: Number(data.margin_right) || 0,
            },
            headerHeight: Number(data.header_height) || 20,
            footerHeight: Number(data.footer_height) || 15,
            showPageNumbers: Boolean(data.show_page_numbers),
            pageNumberFormat: data.page_number_format || "page_of_total",
            pageNumberAlign: data.page_number_align || "center",
            saving: false,
        });
        onWillStart(async () => {
            await Promise.all([this.loadModels(), this.loadPapers()]);
        });
    }

    get title() {
        return _t("Page setup");
    }

    get modelLabel() {
        return _t("Model");
    }

    get paperLabel() {
        return _t("Paper");
    }

    get marginsLabel() {
        return _t("Margins");
    }

    get headerFooterLabel() {
        return _t("Header & footer");
    }

    get pageNumbersLabel() {
        return _t("Page numbers");
    }

    get applyLabel() {
        return _t("Apply");
    }

    get cancelLabel() {
        return _t("Cancel");
    }

    get modelSearchPlaceholder() {
        return _t("Search model…");
    }

    get noModelsLabel() {
        return _t("No models found");
    }

    get loadingLabel() {
        return _t("Loading…");
    }

    get showPageNumbersLabel() {
        return _t("Show page numbers in footer");
    }

    get formatLabel() {
        return _t("Format");
    }

    get alignLabel() {
        return _t("Alignment");
    }

    get headerHeightLabel() {
        return _t("Header height (mm)");
    }

    get footerHeightLabel() {
        return _t("Footer height (mm)");
    }

    get marginPresets() {
        return [
            { id: "normal", label: _t("Normal"), hint: "25.4 mm" },
            { id: "narrow", label: _t("Narrow"), hint: "12.7 mm" },
            { id: "moderate", label: _t("Moderate"), hint: "19.05 mm" },
            { id: "wide", label: _t("Wide"), hint: "50.8 mm" },
            { id: "custom", label: _t("Custom"), hint: _t("mm") },
        ];
    }

    get pageNumberFormats() {
        return PAGE_NUMBER_FORMATS.map((item) => ({
            ...item,
            label: item.label,
        }));
    }

    get alignOptions() {
        return [
            { id: "left", label: _t("Left") },
            { id: "center", label: _t("Center") },
            { id: "right", label: _t("Right") },
        ];
    }

    get pageNumberPreview() {
        const match = PAGE_NUMBER_FORMATS.find(
            (item) => item.id === this.state.pageNumberFormat
        );
        return match ? match.preview : "1 / 3";
    }

    _m2oId(value) {
        if (!value) {
            return false;
        }
        return value.id || value[0] || false;
    }

    _m2oName(value) {
        if (!value) {
            return "";
        }
        return value.display_name || value[1] || "";
    }

    _sameMargin(a, b) {
        return Math.abs(a - b) < 0.05;
    }

    _detectPreset(data) {
        const current = {
            top: Number(data.margin_top) || 0,
            bottom: Number(data.margin_bottom) || 0,
            left: Number(data.margin_left) || 0,
            right: Number(data.margin_right) || 0,
        };
        for (const [name, preset] of Object.entries(MARGIN_PRESETS)) {
            if (
                this._sameMargin(current.top, preset.top) &&
                this._sameMargin(current.bottom, preset.bottom) &&
                this._sameMargin(current.left, preset.left) &&
                this._sameMargin(current.right, preset.right)
            ) {
                return name;
            }
        }
        return "custom";
    }

    async loadModels() {
        this.state.loadingModels = true;
        try {
            const domain = [["transient", "=", false]];
            if (this.state.modelSearch) {
                domain.push("|");
                domain.push(["name", "ilike", this.state.modelSearch]);
                domain.push(["model", "ilike", this.state.modelSearch]);
            }
            this.state.modelOptions = await this.orm.searchRead(
                "ir.model",
                domain,
                ["name", "model"],
                { limit: 50, order: "name" }
            );
        } finally {
            this.state.loadingModels = false;
        }
    }

    async loadPapers() {
        this.state.loadingPapers = true;
        try {
            this.state.paperOptions = await this.orm.searchRead(
                "report.paperformat",
                [["name", "not ilike", "Document Template:"]],
                ["name"],
                { order: "name" }
            );
        } finally {
            this.state.loadingPapers = false;
        }
    }

    async onModelSearchInput(ev) {
        this.state.modelSearch = ev.target.value;
        await this.loadModels();
    }

    selectModel(model) {
        this.state.modelId = model.id;
        this.state.modelName = model.name;
        this.state.modelTechnical = model.model;
    }

    selectPaper(paper) {
        this.state.paperId = paper.id;
        this.state.paperName = paper.name;
    }

    selectMarginPreset(presetId) {
        this.state.marginPreset = presetId;
        const preset = MARGIN_PRESETS[presetId];
        if (preset) {
            this.state.margins = { ...preset };
        }
    }

    onMarginInput(side, ev) {
        const value = parseFloat(ev.target.value);
        this.state.margins[side] = Number.isFinite(value) ? value : 0;
        this.state.marginPreset = "custom";
    }

    onNumberInput(field, ev) {
        const value = parseFloat(ev.target.value);
        this.state[field] = Number.isFinite(value) ? Math.max(0, value) : 0;
    }

    onTogglePageNumbers(ev) {
        this.state.showPageNumbers = Boolean(ev.target.checked);
    }

    selectPageNumberFormat(formatId) {
        this.state.pageNumberFormat = formatId;
    }

    selectPageNumberAlign(alignId) {
        this.state.pageNumberAlign = alignId;
    }

    async apply() {
        this.state.saving = true;
        try {
            const values = {
                model_id: this.state.modelId
                    ? [this.state.modelId, this.state.modelName]
                    : false,
                paperformat_id: this.state.paperId
                    ? [this.state.paperId, this.state.paperName]
                    : false,
                margin_top: this.state.margins.top,
                margin_bottom: this.state.margins.bottom,
                margin_left: this.state.margins.left,
                margin_right: this.state.margins.right,
                header_height: this.state.headerHeight,
                footer_height: this.state.footerHeight,
                show_page_numbers: this.state.showPageNumbers,
                page_number_format: this.state.pageNumberFormat,
                page_number_align: this.state.pageNumberAlign,
            };
            await this.props.record.update(values);
            if (this.props.record.resId) {
                await this.props.record.save();
            }
            if (this.props.onApplied) {
                await this.props.onApplied(values);
            }
            this.props.close();
        } catch (error) {
            this.notification.add(
                error?.data?.message ||
                    error?.message ||
                    _t("Could not apply page setup."),
                { type: "danger" }
            );
        } finally {
            this.state.saving = false;
        }
    }

    cancel() {
        this.props.close();
    }
}
