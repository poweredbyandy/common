from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    pba_total_final_cost = fields.Monetary(
        string="Total costo final (PBA)",
        compute="_compute_pba_final_cost_totals_multicurrency",
        currency_field="currency_id",
    )

    pba_final_cost_totals_multicurrency = fields.Json(
        string="Total costo final (otras monedas)",
        compute="_compute_pba_final_cost_totals_multicurrency",
    )

    def _pba_sum_final_cost_in_order_currency(self):
        self.ensure_one()
        total = 0.0
        line_dt = self.date_order
        if line_dt:
            conv_date = line_dt.date() if hasattr(line_dt, "date") else line_dt
        else:
            conv_date = fields.Date.context_today(self)
        company = self.company_id
        to_c = self.currency_id or company.currency_id
        for line in self.order_line:
            if line.display_type or not line.product_id:
                continue
            qty = line.product_qty or 0.0
            if not qty:
                continue
            fin_unit = line._pba_projected_final_cost_cost_currency()
            total_cc = fin_unit * qty
            from_c = (
                line.product_id.product_tmpl_id.cost_currency_id
                or company.currency_id
            )
            if from_c == to_c:
                total += total_cc
            else:
                total += from_c._convert(
                    total_cc,
                    to_c,
                    company,
                    conv_date,
                    round=True,
                )
        return total

    @api.depends(
        "currency_id",
        "date_order",
        "company_id",
        "order_line.display_type",
        "order_line.product_id",
        "order_line.product_qty",
        "order_line.product_uom",
        "order_line.price_unit",
        "order_line.discount",
        "order_line.pba_cost_freight_percent",
        "order_line.pba_cost_tariff_percent",
        "order_line.pba_cost_operative_percent",
        "order_line.pba_cost_nationalization_percent",
        "order_line.pba_utility_percent",
    )
    def _compute_pba_final_cost_totals_multicurrency(self):
        Currency = self.env["res.currency"]
        for order in self:
            total_po = order._pba_sum_final_cost_in_order_currency()
            order.pba_total_final_cost = total_po
            po_currency = order.currency_id or order.company_id.currency_id
            if not po_currency:
                order.pba_final_cost_totals_multicurrency = False
                continue
            line_dt = order.date_order
            if line_dt:
                conv_date = line_dt.date() if hasattr(line_dt, "date") else line_dt
            else:
                conv_date = fields.Date.context_today(order)
            company = order.company_id
            totals = {}
            for currency in Currency.search(
                [("active", "=", True), ("id", "!=", po_currency.id)]
            ):
                totals[str(currency.id)] = {
                    "currency_id": currency.id,
                    "currency_name": currency.name,
                    "total": po_currency._convert(
                        total_po,
                        currency,
                        company,
                        conv_date,
                        round=True,
                    ),
                }
            order.pba_final_cost_totals_multicurrency = totals or False
