/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { convertCurrency } from "@currency_pos/app/utils/payment_currency_utils";

patch(PosStore.prototype, {
    _pbaGetLinkedSaleOrderIds(order = this.get_order()) {
        if (!order) {
            return [];
        }
        const ids = new Set();
        for (const line of order.get_orderlines()) {
            const saleOrderId = line.sale_order_origin_id?.id;
            if (saleOrderId) {
                ids.add(saleOrderId);
            }
        }
        return [...ids];
    },

    _pbaPosOrderHasSaleOrder(saleOrderId, order = this.get_order()) {
        if (!saleOrderId || !order) {
            return false;
        }
        return this._pbaGetLinkedSaleOrderIds(order).includes(saleOrderId);
    },

    _pbaGetSaleOrderCurrencyIds() {
        const currencyIds = new Set();
        if (this.currency?.id) {
            currencyIds.add(this.currency.id);
        }
        const pricelists = this.models["product.pricelist"]?.getAll?.() || [];
        for (const pricelist of pricelists) {
            const currencyId = pricelist.currency_id?.id;
            if (currencyId) {
                currencyIds.add(currencyId);
            }
        }
        if (this.config?.pricelist_id?.currency_id?.id) {
            currencyIds.add(this.config.pricelist_id.currency_id.id);
        }
        return [...currencyIds];
    },

    _pbaGetQuotationDomain(order = this.get_order()) {
        const currencyIds = this._pbaGetSaleOrderCurrencyIds();
        let domain = [
            ["state", "!=", "cancel"],
            ["invoice_status", "!=", "invoiced"],
            ["currency_id", "in", currencyIds],
            ["amount_unpaid", ">", 0],
        ];
        const linkedSaleOrderIds = this._pbaGetLinkedSaleOrderIds(order);
        if (linkedSaleOrderIds.length) {
            domain = [...domain, ["id", "not in", linkedSaleOrderIds]];
        }
        if (order?.get_partner()) {
            domain = [
                ...domain,
                [
                    "partner_id",
                    "any",
                    [["id", "child_of", [order.get_partner().id]]],
                ],
            ];
        }
        return domain;
    },

    pbaEnsureOrderForQuotation() {
        if (this.get_order()) {
            return this.get_order();
        }
        return this.add_new_order();
    },

    async pbaSyncOrderAfterQuotation(order = this.get_order()) {
        if (!order || order.finalized) {
            return;
        }
        this.addPendingOrder([order.id]);
        try {
            await this.syncAllOrders({ orders: [order] });
        } catch (_error) {
            return;
        }
        if (typeof this.pbaAcquireOrderLock === "function") {
            await this.pbaAcquireOrderLock(order, { silent: true });
        }
    },

    pbaOpenQuotationSelector() {
        this.dialog.add(SelectCreateDialog, {
            resModel: "sale.order",
            noCreate: true,
            multiSelect: false,
            domain: this._pbaGetQuotationDomain(),
            onSelected: async (resIds) => {
                this.ui.block({
                    message: _t("Loading quotation..."),
                });
                try {
                    this.pbaEnsureOrderForQuotation();
                    this.showScreen("ProductScreen");
                    await this.onClickSaleOrder(resIds[0]);
                    await this.pbaSyncOrderAfterQuotation();
                } catch (error) {
                    this.dialog.add(AlertDialog, {
                        title: _t("Error"),
                        body:
                            error?.data?.message ||
                            error?.message ||
                            _t("Could not load the quotation."),
                    });
                } finally {
                    this.ui.unblock();
                }
            },
        });
    },

    async onClickSaleOrder(clickedOrderId) {
        const sale_order = await this._getSaleOrder(clickedOrderId);

        if (this._pbaPosOrderHasSaleOrder(sale_order.id)) {
            this.dialog.add(AlertDialog, {
                title: _t("Sale Order Already Added"),
                body: _t(
                    "The sales order %s is already linked to the current POS order.",
                    sale_order.name
                ),
            });
            return;
        }

        const currentSaleOrigin = this.get_order()
            .get_orderlines()
            .find((line) => line.sale_order_origin_id)?.sale_order_origin_id;
        if (currentSaleOrigin?.id) {
            const linkedSO = await this._getSaleOrder(currentSaleOrigin.id);
            if (
                linkedSO.partner_id?.id !== sale_order.partner_id?.id ||
                linkedSO.partner_invoice_id?.id !== sale_order.partner_invoice_id?.id ||
                linkedSO.partner_shipping_id?.id !== sale_order.partner_shipping_id?.id
            ) {
                this.add_new_order({
                    partner_id: sale_order.partner_id,
                });
            }
        }

        if (this._pbaPosOrderHasSaleOrder(sale_order.id)) {
            this.dialog.add(AlertDialog, {
                title: _t("Sale Order Already Added"),
                body: _t(
                    "The sales order %s is already linked to the current POS order.",
                    sale_order.name
                ),
            });
            return;
        }

        if (sale_order.partner_id) {
            this.get_order().set_partner(sale_order.partner_id);
        }

        const orderFiscalPos = sale_order.fiscal_position_id;
        this.get_order().update({
            fiscal_position_id: orderFiscalPos,
        });

        await this.settleSO(sale_order, orderFiscalPos);
        this.selectOrderLine(this.get_order(), this.get_order().lines.at(-1));
    },

    async _pbaEnsureSaleOrderCurrency(sale_order) {
        if (sale_order?.currency_id?.id || sale_order?.currency_id?.name) {
            return sale_order.currency_id;
        }
        if (typeof sale_order?.currency_id === "number") {
            const currency = this.models["res.currency"]?.get?.(sale_order.currency_id);
            if (currency) {
                sale_order.currency_id = currency;
                return currency;
            }
        }
        if (sale_order?.pricelist_id?.currency_id) {
            return sale_order.pricelist_id.currency_id;
        }
        if (!sale_order?.id) {
            return null;
        }
        const rows = await this.data.read("sale.order", [sale_order.id], ["currency_id"]);
        const currencyId = rows?.[0]?.currency_id;
        if (!currencyId) {
            return null;
        }
        const currency =
            typeof currencyId === "object"
                ? currencyId
                : this.models["res.currency"]?.get?.(currencyId);
        if (currency) {
            sale_order.currency_id = currency;
        }
        return currency || null;
    },

    _pbaSaleOrderNeedsPosCurrencyConversion(sale_order, soCurrency) {
        const soCurrencyId = soCurrency?.id || soCurrency;
        const posCurrencyId = this.currency?.id;
        return Boolean(sale_order && soCurrencyId && posCurrencyId && soCurrencyId !== posCurrencyId);
    },

    _pbaConvertSaleAmountToPos(amount, soCurrency) {
        return convertCurrency(amount || 0, soCurrency, this.currency, this.models);
    },

    async _pbaForceConvertOrderLinesFromSaleOrder(sale_order) {
        const lineIds = (sale_order.order_line || [])
            .map((line) => line.id)
            .filter((id) => typeof id === "number");
        if (!lineIds.length || !this.currency?.id) {
            return;
        }
        const pricesByLineId = await this.data.call(
            "sale.order.line",
            "pba_read_prices_in_pos_currency",
            [lineIds, this.currency.id]
        );
        if (!pricesByLineId) {
            return;
        }
        for (const line of this.get_order().get_orderlines()) {
            const solId = line.sale_order_line_id?.id;
            if (!solId || pricesByLineId[solId] === undefined) {
                continue;
            }
            line.set_unit_price(pricesByLineId[solId]);
            line.price_type = "manual";
        }
    },

    async _pbaPrefetchValuedMoveIds(sale_order) {
        const lineIds = (sale_order?.order_line || [])
            .map((line) => line.id)
            .filter((id) => typeof id === "number");
        if (!lineIds.length) {
            return {};
        }
        try {
            return (
                (await this.data.call(
                    "sale.order.line",
                    "pba_has_valued_move_ids_map",
                    [lineIds]
                )) || {}
            );
        } catch (_error) {
            return {};
        }
    },

    async _pbaWithSettleRpcCache(valuedMoveIdsMap, callback) {
        const data = this.data;
        const originalCall = data.call.bind(data);
        data.call = (model, method, args = [], kwargs = {}, queue = false) => {
            if (model === "sale.order.line" && method === "read_converted") {
                kwargs = {
                    ...kwargs,
                    context: {
                        ...(kwargs.context || {}),
                        pba_pos_currency_id: this.currency.id,
                    },
                };
            }
            if (model === "sale.order.line" && method === "has_valued_move_ids") {
                const lineId = Array.isArray(args[0]) ? args[0][0] : args[0];
                if (lineId in valuedMoveIdsMap) {
                    return Promise.resolve(valuedMoveIdsMap[lineId]);
                }
            }
            return originalCall(model, method, args, kwargs, queue);
        };
        try {
            return await callback();
        } finally {
            data.call = originalCall;
        }
    },

    async settleSO(sale_order, orderFiscalPos) {
        if (this._pbaPosOrderHasSaleOrder(sale_order.id)) {
            this.dialog.add(AlertDialog, {
                title: _t("Sale Order Already Added"),
                body: _t(
                    "The sales order %s is already linked to the current POS order.",
                    sale_order.name
                ),
            });
            return;
        }

        const soCurrency = await this._pbaEnsureSaleOrderCurrency(sale_order);
        const needsConversion = this._pbaSaleOrderNeedsPosCurrencyConversion(
            sale_order,
            soCurrency
        );
        const valuedMoveIdsMap = await this._pbaPrefetchValuedMoveIds(sale_order);

        await this._pbaWithSettleRpcCache(valuedMoveIdsMap, () =>
            super.settleSO(sale_order, orderFiscalPos)
        );

        if (needsConversion) {
            await this._pbaForceConvertOrderLinesFromSaleOrder(sale_order);
        }
    },
});
