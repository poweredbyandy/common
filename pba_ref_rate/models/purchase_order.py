import json

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    pba_ref_rate_show_usd_line = fields.Boolean(
        compute="_compute_pba_ref_rate_usd",
    )
    pba_ref_rate_foreign_per_usd = fields.Float(
        digits=(16, 6),
        string="Moneda por 1 USD",
        compute="_compute_pba_ref_rate_usd",
    )

    @api.depends(
        "currency_id",
        "company_id",
        "company_id.root_id",
        "company_id.currency_id",
        "date_order",
    )
    def _compute_pba_ref_rate_usd(self):
        usd = self.env.ref("base.USD", raise_if_not_found=False)
        Rate = self.env["res.currency.rate"]
        for order in self:
            comp = order.company_id or self.env.company
            root = comp.root_id
            ccy_root = root.currency_id
            cur = order.currency_id
            ref_visible = bool(
                usd and cur and cur != usd and ccy_root and ccy_root != usd
            )
            if not ref_visible:
                order.pba_ref_rate_show_usd_line = False
                order.pba_ref_rate_foreign_per_usd = 0.0
                continue
            rate_date = (
                fields.Date.to_date(order.date_order)
                if order.date_order
                else fields.Date.context_today(order)
            )
            val = Rate.get_foreign_per_usd_at_date(comp, rate_date, cur)
            order.pba_ref_rate_foreign_per_usd = val
            order.pba_ref_rate_show_usd_line = bool(val)

    @api.model
    def _compute_currency_field(self, currency_id):
        date = self.date_order or fields.Date.today()
        to_currency = self.env["res.currency"].browse(currency_id)
        converted = self.env["res.currency.rate"].convert_amount_via_usd_ref(
            self.amount_total,
            self.currency_id,
            to_currency,
            self.company_id,
            date,
        )
        if converted is not None:
            return converted
        return super()._compute_currency_field(currency_id)

    @api.depends(
        "currency_id",
        "amount_total",
        "date_order",
        "company_id.currency_id",
    )
    def _compute_total_currencies(self):
        super()._compute_total_currencies()
        Rate = self.env["res.currency.rate"]
        for order in self:
            if not order.total_currencies:
                continue
            totals = json.loads(order.total_currencies)
            date = order.date_order or fields.Date.today()
            changed = False
            for data in totals.values():
                currency = self.env["res.currency"].browse(data["currency_id"])
                converted = Rate.convert_amount_via_usd_ref(
                    order.amount_total,
                    order.currency_id,
                    currency,
                    order.company_id,
                    date,
                )
                if converted is not None:
                    data["total"] = converted
                    changed = True
            if changed:
                order.total_currencies = json.dumps(totals)
