import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { DatePickerPopup } from "@point_of_sale/app/utils/date_picker_popup/date_picker_popup";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this._pbaEnsureShipLaterDefault();
    },

    onMounted() {
        super.onMounted(...arguments);
        this._pbaEnsureShipLaterDefault();
    },

    _pbaTodayShippingDate() {
        return new Date().toISOString().split("T")[0];
    },

    _pbaIsShipLaterDefault() {
        return Boolean(this.pos.config.ship_later && this.pos.config.pba_ship_later_default);
    },

    _pbaEnsureShipLaterDefault() {
        if (!this._pbaIsShipLaterDefault()) {
            return;
        }
        const order = this.currentOrder;
        if (
            order &&
            !order.finalized &&
            !order.getShippingDate() &&
            !order.getHasRefundLines?.()
        ) {
            order.setShippingDate(this._pbaTodayShippingDate());
        }
    },

    async toggleShippingDatePicker() {
        if (this._pbaIsShipLaterDefault()) {
            this._pbaEnsureShipLaterDefault();
            this.dialog.add(DatePickerPopup, {
                title: _t("Select the shipping date"),
                getPayload: (shippingDate) => {
                    this.currentOrder.setShippingDate(
                        shippingDate || this._pbaTodayShippingDate()
                    );
                },
            });
            return;
        }
        return await super.toggleShippingDatePicker(...arguments);
    },

    get pbaShippingAddressLabel() {
        const order = this.currentOrder;
        const shipping = order?.getPbaPartnerShipping?.();
        if (!shipping) {
            return _t("Local");
        }
        return shipping.contact_address || shipping.name || _t("Delivery address");
    },

    async clickShippingAddress() {
        const order = this.currentOrder;
        if (!order) {
            return;
        }
        const partner = order.get_partner();
        if (!partner) {
            this.dialog.add(AlertDialog, {
                title: _t("Please select the Customer"),
                body: _t(
                    "You need to select the customer before choosing a delivery address."
                ),
            });
            return;
        }

        const addresses = await this._pbaLoadShippingAddressOptions(partner);
        const currentShipping = order.getPbaPartnerShipping();
        const list = [
            {
                id: "local",
                label: _t("Local"),
                isSelected: order.isPbaShippingLocal(),
                item: false,
            },
            ...addresses.map((address) => ({
                id: address.id,
                label: this._pbaFormatShippingAddressLabel(address, partner),
                isSelected: currentShipping && currentShipping.id === address.id,
                item: address,
            })),
        ];

        const selected = await makeAwaitable(this.dialog, SelectionPopup, {
            title: _t("Delivery address"),
            list,
        });
        if (selected === undefined) {
            return;
        }
        order.setPbaPartnerShipping(selected || false);
    },

    _pbaFormatShippingAddressLabel(address, mainPartner) {
        const name = address.name || "";
        const detail =
            address.contact_address ||
            [address.street, address.city].filter(Boolean).join(", ");
        if (address.id === mainPartner.id) {
            return detail ? `${_t("Contact")}: ${detail}` : _t("Contact");
        }
        if (detail && name && detail.includes(name)) {
            return detail;
        }
        return detail ? `${name} - ${detail}` : name;
    },

    async _pbaLoadShippingAddressOptions(partner) {
        const commercialId = partner.parent_id?.id || partner.id;
        let records = [];
        try {
            records = await this.pos.data.searchRead(
                "res.partner",
                [
                    "|",
                    ["id", "=", partner.id],
                    "|",
                    ["id", "=", commercialId],
                    "&",
                    ["parent_id", "=", commercialId],
                    ["type", "in", ["delivery", "other", "contact"]],
                ],
                [
                    "name",
                    "street",
                    "city",
                    "country_id",
                    "contact_address",
                    "type",
                    "parent_id",
                ],
                { limit: 80 }
            );
        } catch (_error) {
            records = [partner];
        }

        const byId = new Map();
        for (const record of records) {
            const partnerRecord =
                this.pos.models["res.partner"].get(record.id) || record;
            byId.set(partnerRecord.id, partnerRecord);
        }
        if (!byId.has(partner.id)) {
            byId.set(partner.id, partner);
        }
        return [...byId.values()];
    },

    _pbaPartnerHasCompleteAddress(partner) {
        return Boolean(
            partner &&
                partner.name &&
                partner.street &&
                partner.city &&
                partner.country_id
        );
    },

    async _isOrderValid(isForceValidate) {
        const order = this.currentOrder;
        const shippingDate = order?.getShippingDate?.();
        const shippingPartner = order?.getPbaPartnerShipping?.();
        const skipCoreAddressCheck = Boolean(shippingDate);

        if (
            shippingDate &&
            shippingPartner &&
            !this._pbaPartnerHasCompleteAddress(shippingPartner)
        ) {
            this.dialog.add(AlertDialog, {
                title: _t("Incorrect address for shipping"),
                body: _t("The selected customer needs an address."),
            });
            return false;
        }

        if (skipCoreAddressCheck) {
            order.shipping_date = false;
            try {
                return await super._isOrderValid(isForceValidate);
            } finally {
                order.shipping_date = shippingDate;
            }
        }
        return await super._isOrderValid(isForceValidate);
    },
});
