/** @odoo-module **/
// Copyright 2026 Anderson Armeya
// License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import {ExchangeRateTooltip} from "@l10n_ve_exchange_rates/components/exchange_rate_tooltip/exchange_rate_tooltip";
import {registry} from "@web/core/registry";
import {formatFloat} from "@web/views/fields/formatters";

export class ExchangeRateSpreadTooltip extends ExchangeRateTooltip {
    setup() {
        super.setup();
        this.state.spreads = [];
    }
    async getRates() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "res.currency",
                "get_exchange_rates",
                [],
                {}
            );
            this.state.rates = data.rates;
            this.state.company_currency = data.company_currency;
            this.state.featured = data.featured || false;
            this.state.spreads = data.spreads || [];
        } catch {
            this.state.rates = [];
            this.state.spreads = [];
        } finally {
            this.state.loading = false;
        }
    }
    formatSpread(value) {
        const sign = value > 0 ? "+" : "";
        return sign + formatFloat(value, {digits: [2, 2]}) + "%";
    }
    formatDetail(spread) {
        const from = formatFloat(spread.from_rate, {digits: [0, 6]});
        const to = formatFloat(spread.to_rate, {digits: [0, 6]});
        const ratio = formatFloat(spread.ratio, {digits: [0, 4]});
        return (
            `${from} / ${to} ${spread.company_currency_symbol} · ` +
            `1 ${spread.from_name} ≈ ${ratio} ${spread.to_name}`
        );
    }
}

const systrayRegistry = registry.category("systray");
systrayRegistry.remove("ExchangeRateTooltip");
systrayRegistry.add("ExchangeRateTooltip", {
    Component: ExchangeRateSpreadTooltip,
    sequence: 1,
});
