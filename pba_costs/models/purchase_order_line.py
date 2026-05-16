from odoo import api, fields, models
from odoo.tools.float_utils import float_compare


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    pba_cost_freight_percent = fields.Float(string="% Flete (PBA)")
    pba_cost_tariff_percent = fields.Float(string="% Arancel (PBA)")
    pba_cost_operative_percent = fields.Float(string="% Operativo (PBA)")
    pba_cost_nationalization_percent = fields.Float(string="% Nacionalización (PBA)")

    pba_cost_freight_percent_baseline = fields.Float(string="Referencia % flete")
    pba_cost_tariff_percent_baseline = fields.Float(string="Referencia % arancel")
    pba_cost_operative_percent_baseline = fields.Float(string="Referencia % operativo")
    pba_cost_nationalization_percent_baseline = fields.Float(
        string="Referencia % nacionalización",
    )

    pba_utility_percent = fields.Float(string="% Utilidad (PBA)")
    pba_utility_percent_baseline = fields.Float(string="Referencia % utilidad")

    pba_projected_final_cost = fields.Monetary(
        string="Costo final (PBA)",
        currency_field="pba_cost_pba_currency_id",
        compute="_compute_pba_utility_sale_fields",
    )

    pba_utility_margin_amount = fields.Float(
        string="Importe utilidad (PBA)",
        compute="_compute_pba_utility_sale_fields",
        digits="Product Price",
    )
    pba_sale_price_suggested = fields.Float(
        string="P.V.P. sugerido (PBA)",
        compute="_compute_pba_utility_sale_fields",
        digits="Product Price",
    )
    pba_last_sale_price = fields.Float(
        string="Último P.V. venta (PBA)",
        compute="_compute_pba_last_sale_price",
        digits="Product Price",
    )
    pba_sale_price_unit = fields.Float(
        string="Precio venta unit. (PBA)",
        digits="Product Price",
    )
    pba_sale_price_unit_baseline = fields.Float(string="Referencia precio venta PBA")

    pba_cost_freight = fields.Monetary(
        string="Importe flete (PBA)",
        currency_field="pba_cost_pba_currency_id",
        compute="_compute_pba_cost_amounts",
    )
    pba_cost_tariff = fields.Monetary(
        string="Importe arancel (PBA)",
        currency_field="pba_cost_pba_currency_id",
        compute="_compute_pba_cost_amounts",
    )
    pba_cost_operative = fields.Monetary(
        string="Importe operativo (PBA)",
        currency_field="pba_cost_pba_currency_id",
        compute="_compute_pba_cost_amounts",
    )
    pba_cost_nationalization = fields.Monetary(
        string="Importe nacionalización (PBA)",
        currency_field="pba_cost_pba_currency_id",
        compute="_compute_pba_cost_amounts",
    )
    pba_cost_pba_currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_pba_cost_pba_currency_id",
    )

    @api.depends("product_id", "company_id")
    def _compute_pba_cost_pba_currency_id(self):
        for line in self:
            if line.product_id:
                line.pba_cost_pba_currency_id = (
                    line.product_id.product_tmpl_id.cost_currency_id
                    or line.company_id.currency_id
                )
            else:
                line.pba_cost_pba_currency_id = line.company_id.currency_id

    @api.depends(
        "display_type",
        "product_id",
        "product_uom",
        "price_unit_discounted",
        "currency_id",
        "order_id.date_order",
        "company_id",
        "pba_cost_pba_currency_id",
        "pba_cost_freight_percent",
        "pba_cost_tariff_percent",
        "pba_cost_operative_percent",
        "pba_cost_nationalization_percent",
    )
    def _compute_pba_cost_amounts(self):
        for line in self:
            if line.display_type or not line.product_id:
                line.pba_cost_freight = 0.0
                line.pba_cost_tariff = 0.0
                line.pba_cost_operative = 0.0
                line.pba_cost_nationalization = 0.0
                continue
            base = line._pba_cost_base_in_product_cost_currency()
            line.pba_cost_freight = base * (line.pba_cost_freight_percent or 0.0)
            line.pba_cost_tariff = base * (line.pba_cost_tariff_percent or 0.0)
            line.pba_cost_operative = base * (line.pba_cost_operative_percent or 0.0)
            line.pba_cost_nationalization = base * (
                line.pba_cost_nationalization_percent or 0.0
            )

    @api.depends(
        "display_type",
        "product_id",
        "product_uom",
        "price_unit_discounted",
        "currency_id",
        "order_id.date_order",
        "company_id",
        "pba_cost_pba_currency_id",
        "pba_cost_freight",
        "pba_cost_tariff",
        "pba_cost_operative",
        "pba_cost_nationalization",
        "pba_utility_percent",
    )
    def _compute_pba_utility_sale_fields(self):
        for line in self:
            if line.display_type or not line.product_id:
                line.pba_projected_final_cost = 0.0
                line.pba_utility_margin_amount = 0.0
                line.pba_sale_price_suggested = 0.0
                continue
            fin = line._pba_projected_final_cost_cost_currency()
            line.pba_projected_final_cost = fin
            util = line.pba_utility_percent or 0.0
            line.pba_utility_margin_amount = fin * util
            line.pba_sale_price_suggested = fin * (1.0 + util)

    @api.depends(
        "display_type",
        "product_id",
        "product_id.product_tmpl_id.pba_last_sale_price",
        "pba_cost_pba_currency_id",
        "company_id",
        "order_id.date_order",
    )
    def _compute_pba_last_sale_price(self):
        for line in self:
            if line.display_type or not line.product_id:
                line.pba_last_sale_price = 0.0
                continue
            tmpl = line.product_id.product_tmpl_id
            line_dt = line.order_id.date_order
            if line_dt:
                conv_date = line_dt.date() if hasattr(line_dt, "date") else line_dt
            else:
                conv_date = fields.Date.context_today(line)
            line.pba_last_sale_price = tmpl._pba_convert_sale_amount_to_cost_currency(
                tmpl.pba_last_sale_price,
                conv_date,
            )

    def _pba_cost_base_in_product_cost_currency(self):
        self.ensure_one()
        if self.display_type or not self.product_id:
            return 0.0
        tmpl = self.product_id.product_tmpl_id
        to_currency = tmpl.cost_currency_id or self.company_id.currency_id
        line_uom = self.product_uom or self.product_id.uom_po_id or self.product_id.uom_id
        if not line_uom:
            return 0.0
        price_uom = line_uom._compute_price(
            self.price_unit_discounted,
            self.product_id.uom_id,
        )
        line_dt = self.order_id.date_order
        if line_dt:
            conv_date = line_dt.date() if hasattr(line_dt, "date") else line_dt
        else:
            conv_date = fields.Date.context_today(self)
        return self.currency_id._convert(
            price_uom,
            to_currency,
            self.company_id,
            conv_date,
            round=True,
        )

    def _pba_projected_final_cost_cost_currency(self):
        self.ensure_one()
        if self.display_type or not self.product_id:
            return 0.0
        base = self._pba_cost_base_in_product_cost_currency()
        return (
            base
            + (self.pba_cost_freight or 0.0)
            + (self.pba_cost_tariff or 0.0)
            + (self.pba_cost_operative or 0.0)
            + (self.pba_cost_nationalization or 0.0)
        )

    def _pba_sale_price_for_template_list_price(self):
        self.ensure_one()
        tmpl = self.product_id.product_tmpl_id
        from_c = tmpl.cost_currency_id or self.company_id.currency_id
        to_c = tmpl.currency_id or self.company_id.currency_id
        line_dt = self.order_id.date_order
        if line_dt:
            conv_date = line_dt.date() if hasattr(line_dt, "date") else line_dt
        else:
            conv_date = fields.Date.context_today(self)
        amount = float(self.pba_sale_price_unit or 0.0)
        if from_c == to_c:
            return amount
        return from_c._convert(
            amount,
            to_c,
            self.company_id,
            conv_date,
            round=True,
        )

    @api.onchange("product_id")
    def _onchange_product_id_pba_cost_percents(self):
        for line in self:
            if line.display_type or not line.product_id:
                continue
            tmpl = line.product_id.product_tmpl_id
            line.pba_cost_freight_percent = tmpl.pba_cost_freight_percent
            line.pba_cost_tariff_percent = tmpl.pba_cost_tariff_percent
            line.pba_cost_operative_percent = tmpl.pba_cost_operative_percent
            line.pba_cost_nationalization_percent = (
                tmpl.pba_cost_nationalization_percent
            )
            line.pba_cost_freight_percent_baseline = line.pba_cost_freight_percent
            line.pba_cost_tariff_percent_baseline = line.pba_cost_tariff_percent
            line.pba_cost_operative_percent_baseline = line.pba_cost_operative_percent
            line.pba_cost_nationalization_percent_baseline = (
                line.pba_cost_nationalization_percent
            )
            line.pba_utility_percent = tmpl.pba_utility_percent
            line.pba_utility_percent_baseline = line.pba_utility_percent
            line.pba_sale_price_unit = line.pba_sale_price_suggested
            line.pba_sale_price_unit_baseline = line.pba_sale_price_unit

    @api.onchange(
        "pba_utility_percent",
        "pba_cost_freight_percent",
        "pba_cost_tariff_percent",
        "pba_cost_operative_percent",
        "pba_cost_nationalization_percent",
        "price_unit",
        "discount",
        "product_qty",
        "product_uom",
    )
    def _onchange_pba_refresh_sale_price_unit_from_suggestion(self):
        for line in self:
            if line.display_type or not line.product_id:
                continue
            line.pba_sale_price_unit = line.pba_sale_price_suggested

    @api.model
    def _pba_cost_percent_field_map(self):
        return (
            ("pba_cost_freight_percent", "pba_cost_freight_percent_baseline"),
            ("pba_cost_tariff_percent", "pba_cost_tariff_percent_baseline"),
            ("pba_cost_operative_percent", "pba_cost_operative_percent_baseline"),
            (
                "pba_cost_nationalization_percent",
                "pba_cost_nationalization_percent_baseline",
            ),
            ("pba_utility_percent", "pba_utility_percent_baseline"),
        )

    @api.model
    def _pba_price_precision_digits(self):
        return self.env["decimal.precision"].precision_get("Product Price")

    @api.model
    def _pba_prepare_vals_pba_cost_defaults(self, vals):
        vals = dict(vals)
        if vals.get("display_type"):
            return vals
        pid = vals.get("product_id")
        if not pid:
            return vals
        product = self.env["product.product"].browse(pid)
        if not product:
            return vals
        tmpl = product.product_tmpl_id
        for pct_f, base_f in self._pba_cost_percent_field_map():
            if pct_f not in vals:
                vals[pct_f] = tmpl[pct_f]
            if base_f not in vals:
                vals[base_f] = vals[pct_f]
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        had_sale_unit = [bool(v.get("pba_sale_price_unit")) for v in vals_list]
        cleaned = [self._pba_prepare_vals_pba_cost_defaults(v) for v in vals_list]
        lines = super().create(cleaned)
        for line, had in zip(lines, had_sale_unit):
            if line.display_type or not line.product_id:
                continue
            if had:
                super(PurchaseOrderLine, line).write(
                    {"pba_sale_price_unit_baseline": line.pba_sale_price_unit}
                )
                continue
            su = line.pba_sale_price_suggested
            super(PurchaseOrderLine, line).write(
                {"pba_sale_price_unit": su, "pba_sale_price_unit_baseline": su}
            )
        lines._pba_invalidate_product_template_last_cost()
        return lines

    def write(self, vals):
        vals = dict(vals)
        product_changed = (
            "product_id" in vals and vals.get("product_id") and not vals.get("display_type")
        )
        if product_changed:
            vals = self._pba_prepare_vals_pba_cost_defaults(vals)
        old_templates = self.product_id.product_tmpl_id
        res = super().write(vals)
        if product_changed:
            for line in self:
                if line.display_type or not line.product_id:
                    continue
                su = line.pba_sale_price_suggested
                super(PurchaseOrderLine, line).write(
                    {"pba_sale_price_unit": su, "pba_sale_price_unit_baseline": su}
                )
        (old_templates | self.product_id.product_tmpl_id)._pba_invalidate_last_cost()
        return res

    def unlink(self):
        templates = self.product_id.product_tmpl_id
        res = super().unlink()
        templates._pba_invalidate_last_cost()
        return res

    def _pba_invalidate_product_template_last_cost(self):
        self.product_id.product_tmpl_id._pba_invalidate_last_cost()

    def _pba_percent_differs(self, current, baseline):
        return (
            float_compare(
                current or 0.0,
                baseline or 0.0,
                precision_digits=6,
            )
            != 0
        )

    def _pba_price_differs(self, current, baseline):
        digits = self._pba_price_precision_digits()
        return (
            float_compare(
                current or 0.0,
                baseline or 0.0,
                precision_digits=digits,
            )
            != 0
        )

    def _pba_build_template_sync_vals_from_line(self):
        self.ensure_one()
        if self.display_type or not self.product_id:
            return {}
        tmpl_vals = {}
        if self._pba_percent_differs(
            self.pba_cost_freight_percent,
            self.pba_cost_freight_percent_baseline,
        ):
            tmpl_vals["pba_cost_freight_percent"] = self.pba_cost_freight_percent
        if self._pba_percent_differs(
            self.pba_cost_tariff_percent,
            self.pba_cost_tariff_percent_baseline,
        ):
            tmpl_vals["pba_cost_tariff_percent"] = self.pba_cost_tariff_percent
        if self._pba_percent_differs(
            self.pba_cost_operative_percent,
            self.pba_cost_operative_percent_baseline,
        ):
            tmpl_vals["pba_cost_operative_percent"] = self.pba_cost_operative_percent
        if self._pba_percent_differs(
            self.pba_cost_nationalization_percent,
            self.pba_cost_nationalization_percent_baseline,
        ):
            tmpl_vals["pba_cost_nationalization_percent"] = (
                self.pba_cost_nationalization_percent
            )
        if self._pba_percent_differs(
            self.pba_utility_percent,
            self.pba_utility_percent_baseline,
        ):
            tmpl_vals["pba_utility_percent"] = self.pba_utility_percent
        if self._pba_price_differs(
            self.pba_sale_price_unit,
            self.pba_sale_price_unit_baseline,
        ):
            tmpl_vals["list_price"] = self._pba_sale_price_for_template_list_price()
        return tmpl_vals
