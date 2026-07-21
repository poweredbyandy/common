from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.model
    def _compute_currency_field(self, currency_id):
        date = self.order_id.date_order or fields.Date.today()
        to_currency = self.env["res.currency"].browse(currency_id)
        converted = self.env["res.currency.rate"].convert_amount_via_usd_ref(
            self.price_subtotal,
            self.currency_id,
            to_currency,
            self.order_id.company_id,
            date,
        )
        if converted is not None:
            return converted
        return super()._compute_currency_field(currency_id)

    @api.model
    def _compute_price_unit_currency_field(self, currency_id):
        date = self.order_id.date_order or fields.Date.today()
        to_currency = self.env["res.currency"].browse(currency_id)
        converted = self.env["res.currency.rate"].convert_amount_via_usd_ref(
            self.price_unit,
            self.currency_id,
            to_currency,
            self.order_id.company_id,
            date,
        )
        if converted is not None:
            return converted
        return super()._compute_price_unit_currency_field(currency_id)
