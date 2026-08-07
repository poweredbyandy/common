/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { ask } from "@point_of_sale/app/store/make_awaitable_dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(ControlButtons.prototype, {
    _getQuotationLinesFromOrder(order) {
        const tipProductId = order.config.tip_product_id?.id;
        return order.get_orderlines().filter((line) => {
            const product = line.get_product();
            if (!product) {
                return false;
            }
            if (tipProductId && product.id === tipProductId) {
                return false;
            }
            if (line.combo_line_ids?.length) {
                return false;
            }
            return true;
        });
    },

    _prepareQuotationPayload(order) {
        const partner = order.get_partner();
        const lines = this._getQuotationLinesFromOrder(order).map((line) => {
            const product = line.get_product();
            const taxValues = line.prepareBaseLineForTaxesComputationExtraValues();
            const taxes = taxValues.tax_ids || [];
            const taxIds = taxes.map((tax) => tax.id);
            return {
                product_id: product.id,
                qty: line.get_quantity(),
                price_unit: line.get_unit_price(),
                discount: line.get_discount(),
                product_uom_id: line.get_unit()?.id || product.uom_id?.id || false,
                name: line.get_full_product_name(),
                tax_ids: taxIds,
            };
        });
        const pricelist = order.pricelist_id || this.pos.config.pricelist_id;
        return {
            partner_id: partner.id,
            company_id: order.company?.id || this.pos.company?.id || false,
            user_id: this.pos.user?.id || false,
            config_id: this.pos.config?.id || false,
            pos_reference: order.pos_reference || false,
            note: order.general_note || false,
            pricelist_id: pricelist?.id || false,
            pos_currency_id: this.pos.currency?.id || false,
            fiscal_position_id: order.fiscal_position_id?.id || false,
            lines,
        };
    },

    async onClickGenerateQuotation() {
        const order = this.pos.get_order();
        if (!order || order.is_empty()) {
            this.dialog.add(AlertDialog, {
                title: _t("Empty Order"),
                body: _t("Add products before generating a quotation."),
            });
            return;
        }
        if (!order.get_partner()) {
            this.dialog.add(AlertDialog, {
                title: _t("Customer Required"),
                body: _t("Please select a customer before generating a quotation."),
            });
            return;
        }
        const quotationLines = this._getQuotationLinesFromOrder(order);
        if (!quotationLines.length) {
            this.dialog.add(AlertDialog, {
                title: _t("Empty Order"),
                body: _t("There are no products that can be transferred to a quotation."),
            });
            return;
        }

        const confirmed = await ask(this.dialog, {
            title: _t("Generar Presupuesto"),
            body: _t(
                "A quotation will be created with the current products and the POS order will be deleted. Do you want to continue?"
            ),
        });
        if (!confirmed) {
            return;
        }

        try {
            const result = await this.pos.data.call(
                "sale.order",
                "create_quotation_from_pos",
                [this._prepareQuotationPayload(order)]
            );
            const deleted = await this.pos.deleteOrders([order]);
            if (!deleted) {
                this.notification.add(
                    _t(
                        "Quotation %s was created, but the POS order could not be deleted.",
                        result.name
                    ),
                    { type: "warning" }
                );
                return;
            }
            if (order.uiState) {
                order.uiState.displayed = false;
            }
            this.pos.afterOrderDeletion();
            if (this.props.close) {
                this.props.close();
            }
            this.notification.add(_t("Quotation %s created successfully.", result.name), {
                type: "success",
            });

        } catch (error) {
            this.dialog.add(AlertDialog, {
                title: _t("Error"),
                body:
                    error?.data?.message ||
                    error?.message ||
                    _t("Could not create the quotation."),
            });
        }
    },
});
