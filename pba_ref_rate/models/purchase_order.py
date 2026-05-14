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
