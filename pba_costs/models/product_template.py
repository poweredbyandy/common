import logging

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.safe_eval import safe_eval

from .pba_constants import (
    DEFAULT_PBA_FINAL_COST_FORMULA,
    _pba_final_cost_formula_variable_names,
    pba_final_cost_dummy_eval_context,
)

_logger = logging.getLogger(__name__)

PBA_COST_IMPORTE_HELP = (
    "Calculado: último costo del producto (pba_last_cost) × % aplicado."
)

PBA_COST_HISTORY_TITLES = {
    "freight": "Historial — Costo Flete",
    "tariff": "Historial — Costo Arancel",
    "operative": "Historial — Costo Operativo",
    "nationalization": "Historial — Costo Nacionalización",
}

COST_FIELD_GROUPS = (
    ("freight", ("pba_cost_freight", "pba_cost_freight_percent")),
    ("tariff", ("pba_cost_tariff", "pba_cost_tariff_percent")),
    ("operative", ("pba_cost_operative", "pba_cost_operative_percent")),
    (
        "nationalization",
        ("pba_cost_nationalization", "pba_cost_nationalization_percent"),
    ),
)

_LEGACY_OPERATION_TOTAL_KEYS = (
    "pba_cost_freight_operation_total",
    "pba_cost_tariff_operation_total",
    "pba_cost_operative_operation_total",
    "pba_cost_nationalization_operation_total",
)


def _pba_strip_legacy_write_vals(vals):
    vals = dict(vals)
    for k in _LEGACY_OPERATION_TOTAL_KEYS:
        vals.pop(k, None)
    return vals


class ProductTemplate(models.Model):
    _inherit = "product.template"

    pba_cost_freight_percent = fields.Float(string="% aplicado (Flete)")

    pba_cost_tariff_percent = fields.Float(string="% aplicado (Arancel)")

    pba_cost_operative_percent = fields.Float(string="% aplicado (Operativo)")

    pba_cost_nationalization_percent = fields.Float(
        string="% aplicado (Nacionalización)",
    )

    pba_utility_percent = fields.Float(string="% Utilidad")

    pba_cost_discount_percent = fields.Float(
        string="% Descuento de Costo",
        help="Descuento adicional sobre el remanente tras el descuento comercial "
        "de compra. Se usa como base de los costos PBA.",
    )

    pba_cost_discount = fields.Monetary(
        string="Descuento de Costo",
        currency_field="cost_currency_id",
        compute="_compute_pba_cost_discount",
        store=True,
        help="Importe: último costo × % Descuento de Costo.",
    )

    pba_utility_margin_amount = fields.Monetary(
        string="Importe utilidad (sobre costo final)",
        currency_field="cost_currency_id",
        compute="_compute_pba_utility_margin_amount",
    )

    pba_suggested_list_price = fields.Float(
        string="Precio venta sugerido",
        compute="_compute_pba_suggested_list_price",
        digits="Product Price",
    )

    pba_last_sale_price = fields.Float(
        string="Último precio de venta",
        compute="_compute_pba_last_sale_price",
        digits="Product Price",
        help="Precio unitario de la última venta confirmada (descuento aplicado), "
        "en la UdM del producto y moneda de venta. Si no hay ventas, se usa el precio de venta actual.",
    )

    pba_cost_freight = fields.Monetary(
        string="Costo Flete",
        currency_field="cost_currency_id",
        compute="_compute_pba_cost_freight",
        store=True,
        help=PBA_COST_IMPORTE_HELP,
    )

    pba_cost_tariff = fields.Monetary(
        string="Costo Arancel",
        currency_field="cost_currency_id",
        compute="_compute_pba_cost_tariff",
        store=True,
        help=PBA_COST_IMPORTE_HELP,
    )

    pba_cost_operative = fields.Monetary(
        string="Costo Operativo",
        currency_field="cost_currency_id",
        compute="_compute_pba_cost_operative",
        store=True,
        help=PBA_COST_IMPORTE_HELP,
    )

    pba_cost_nationalization = fields.Monetary(
        string="Costo Nacionalización",
        currency_field="cost_currency_id",
        compute="_compute_pba_cost_nationalization",
        store=True,
        help=PBA_COST_IMPORTE_HELP,
    )

    pba_cost_history_ids = fields.One2many(
        "pba.product.cost.history",
        "product_tmpl_id",
        string="Historial de costos",
    )

    pba_last_cost = fields.Monetary(
        string="Último costo",
        compute="_compute_pba_last_cost",
        currency_field="cost_currency_id",
        help="Precio unitario de la última compra confirmada (descuento aplicado), "
        "en la UdM del producto y moneda de costo.",
    )

    pba_final_cost = fields.Monetary(
        string="Costo final",
        compute="_compute_pba_final_cost",
        currency_field="cost_currency_id",
        help="Calculado con la fórmula global (Ajustes ▸ PBA Costos o edición en la ficha del producto "
        "para usuarios con grupo Características técnicas). Por defecto: último costo más los cuatro importes PBA.",
    )

    pba_session_debug = fields.Boolean(
        string="Sesión en modo desarrollador",
        compute="_compute_pba_session_debug",
    )

    pba_formula_variables_reference = fields.Text(
        string="Variables disponibles (fórmula)",
        compute="_compute_pba_formula_variables_reference",
    )

    pba_cost_display_currency_id = fields.Many2one(
        "res.currency",
        string="Ver importes en moneda",
    )

    pba_standard_price_display_ccy = fields.Monetary(
        string="Costo promedio (ref.)",
        currency_field="pba_cost_display_currency_id",
        compute="_compute_pba_costs_display_currency_amounts",
    )
    pba_last_cost_display_ccy = fields.Monetary(
        string="Último costo (ref.)",
        currency_field="pba_cost_display_currency_id",
        compute="_compute_pba_costs_display_currency_amounts",
    )
    pba_final_cost_display_ccy = fields.Monetary(
        string="Costo final (ref.)",
        currency_field="pba_cost_display_currency_id",
        compute="_compute_pba_costs_display_currency_amounts",
    )
    pba_cost_freight_display_ccy = fields.Monetary(
        string="Flete (ref.)",
        currency_field="pba_cost_display_currency_id",
        compute="_compute_pba_costs_display_currency_amounts",
    )
    pba_cost_tariff_display_ccy = fields.Monetary(
        string="Arancel (ref.)",
        currency_field="pba_cost_display_currency_id",
        compute="_compute_pba_costs_display_currency_amounts",
    )
    pba_cost_operative_display_ccy = fields.Monetary(
        string="Operativo (ref.)",
        currency_field="pba_cost_display_currency_id",
        compute="_compute_pba_costs_display_currency_amounts",
    )
    pba_cost_nationalization_display_ccy = fields.Monetary(
        string="Nacionalización (ref.)",
        currency_field="pba_cost_display_currency_id",
        compute="_compute_pba_costs_display_currency_amounts",
    )

    pba_final_cost_formula_edit = fields.Text(
        string="Fórmula global del costo final",
        compute="_compute_pba_final_cost_formula_edit",
        inverse="_inverse_pba_final_cost_formula_edit",
        help="Misma expresión global para todos los productos. Visible y editable en el producto solo "
        "para usuarios con el grupo Características técnicas (base.group_no_one). Ver ayuda en Ajustes ▸ PBA Costos.",
    )

    def _pba_find_last_purchase_order_line(self):
        self.ensure_one()
        Pol = self.env["purchase.order.line"]
        variants = self.product_variant_ids
        if not variants:
            return Pol.browse()
        try:
            return Pol.search(
                [
                    ("product_id", "in", variants.ids),
                    ("state", "in", ["purchase", "done"]),
                    ("display_type", "=", False),
                ],
                order="date_approve desc, date_order desc, id desc",
                limit=1,
            )
        except AccessError:
            return Pol.browse()

    def _pba_find_last_sale_order_line(self):
        self.ensure_one()
        Sol = self.env["sale.order.line"]
        variants = self.product_variant_ids
        if not variants:
            return Sol.browse()
        line_domain = [
            ("product_id", "in", variants.ids),
            ("display_type", "=", False),
            ("is_downpayment", "=", False),
            ("is_expense", "=", False),
        ]
        try:
            orders = self.env["sale.order"].search(
                [
                    ("state", "in", ["sale", "done"]),
                    ("order_line", "any", line_domain),
                ],
                order="date_order desc, id desc",
                limit=1,
            )
            if not orders:
                return Sol.browse()
            lines = orders.order_line.filtered_domain(line_domain)
            if not lines:
                return Sol.browse()
            return lines.sorted("id", reverse=True)[:1]
        except AccessError:
            return Sol.browse()

    def _pba_last_sale_line_conversion_date(self, line):
        if not line:
            return fields.Date.context_today(self)
        order_dt = line.order_id.date_order
        if order_dt:
            return order_dt.date() if hasattr(order_dt, "date") else order_dt
        return fields.Date.context_today(self)

    def _pba_sale_line_unit_price_discounted(self, line):
        discount_factor = 1.0 - (line.discount or 0.0) / 100.0
        return (line.price_unit or 0.0) * discount_factor

    def _pba_last_purchase_line_conversion_date(self, line):
        if not line:
            return fields.Date.context_today(self)
        line_dt = line.date_approve or line.date_order
        if line_dt:
            return line_dt.date() if hasattr(line_dt, "date") else line_dt
        return fields.Date.context_today(self)

    @api.depends(
        "product_variant_ids",
        "cost_currency_id",
        "standard_price",
    )
    def _compute_pba_last_cost(self):
        for template in self:
            fallback = template.standard_price or 0.0
            line = template._pba_find_last_purchase_order_line()
            if not line:
                template.pba_last_cost = fallback
                continue
            try:
                price_uom = line.product_uom._compute_price(
                    line.price_unit_discounted,
                    line.product_id.uom_id,
                )
                date = template._pba_last_purchase_line_conversion_date(line)
                to_currency = template.cost_currency_id or line.company_id.currency_id
                template.pba_last_cost = line.currency_id._convert(
                    price_uom,
                    to_currency,
                    line.company_id,
                    date,
                    round=True,
                )
            except AccessError:
                template.pba_last_cost = fallback

    @api.depends(
        "product_variant_ids",
        "currency_id",
        "company_id",
        "list_price",
    )
    def _compute_pba_last_sale_price(self):
        for template in self:
            fallback = template.list_price or 0.0
            line = template._pba_find_last_sale_order_line()
            if not line:
                template.pba_last_sale_price = fallback
                continue
            try:
                price_disc = template._pba_sale_line_unit_price_discounted(line)
                price_uom = line.product_uom._compute_price(
                    price_disc,
                    line.product_id.uom_id,
                )
                date = template._pba_last_sale_line_conversion_date(line)
                to_currency = template.currency_id or line.company_id.currency_id
                template.pba_last_sale_price = line.currency_id._convert(
                    price_uom,
                    to_currency,
                    line.company_id,
                    date,
                    round=True,
                )
            except AccessError:
                template.pba_last_sale_price = fallback

    def _pba_convert_sale_amount_to_cost_currency(self, amount, rate_date=None):
        self.ensure_one()
        from_currency = self.currency_id or self.company_id.currency_id
        to_currency = self.cost_currency_id or self.company_id.currency_id
        if not from_currency or not to_currency or from_currency == to_currency:
            return float(amount or 0.0)
        conv_date = (
            rate_date
            if rate_date is not None
            else fields.Date.context_today(self)
        )
        return from_currency._convert(
            float(amount or 0.0),
            to_currency,
            self.company_id,
            conv_date,
            round=True,
        )

    def _pba_cost_base_after_cost_discount(self):
        self.ensure_one()
        last = self.pba_last_cost or 0.0
        return last * (1.0 - (self.pba_cost_discount_percent or 0.0))

    @api.depends("pba_last_cost", "pba_cost_discount_percent")
    def _compute_pba_cost_discount(self):
        for rec in self:
            base = rec.pba_last_cost or 0.0
            pct = rec.pba_cost_discount_percent or 0.0
            rec.pba_cost_discount = base * pct

    @api.depends("pba_last_cost", "pba_cost_discount_percent", "pba_cost_freight_percent")
    def _compute_pba_cost_freight(self):
        for rec in self:
            base = rec._pba_cost_base_after_cost_discount()
            pct = rec.pba_cost_freight_percent or 0.0
            rec.pba_cost_freight = base * pct

    @api.depends("pba_last_cost", "pba_cost_discount_percent", "pba_cost_tariff_percent")
    def _compute_pba_cost_tariff(self):
        for rec in self:
            base = rec._pba_cost_base_after_cost_discount()
            pct = rec.pba_cost_tariff_percent or 0.0
            rec.pba_cost_tariff = base * pct

    @api.depends("pba_last_cost", "pba_cost_discount_percent", "pba_cost_operative_percent")
    def _compute_pba_cost_operative(self):
        for rec in self:
            base = rec._pba_cost_base_after_cost_discount()
            pct = rec.pba_cost_operative_percent or 0.0
            rec.pba_cost_operative = base * pct

    @api.depends(
        "pba_last_cost",
        "pba_cost_discount_percent",
        "pba_cost_nationalization_percent",
    )
    def _compute_pba_cost_nationalization(self):
        for rec in self:
            base = rec._pba_cost_base_after_cost_discount()
            pct = rec.pba_cost_nationalization_percent or 0.0
            rec.pba_cost_nationalization = base * pct

    @api.depends("pba_final_cost", "pba_utility_percent")
    def _compute_pba_utility_margin_amount(self):
        for rec in self:
            rec.pba_utility_margin_amount = (rec.pba_final_cost or 0.0) * (
                rec.pba_utility_percent or 0.0
            )

    @api.depends(
        "pba_final_cost",
        "pba_utility_percent",
        "currency_id",
        "cost_currency_id",
        "company_id",
    )
    def _compute_pba_suggested_list_price(self):
        for rec in self:
            fin = rec.pba_final_cost or 0.0
            to_c = rec.currency_id or rec.company_id.currency_id
            from_c = rec.cost_currency_id or rec.company_id.currency_id
            if not to_c:
                rec.pba_suggested_list_price = 0.0
                continue
            if from_c == to_c:
                fin_sale = fin
            else:
                fin_sale = from_c._convert(
                    fin,
                    to_c,
                    rec.company_id,
                    fields.Date.context_today(rec),
                    round=True,
                )
            rec.pba_suggested_list_price = fin_sale * (
                1.0 + (rec.pba_utility_percent or 0.0)
            )

    @api.depends(
        "pba_last_cost",
        "pba_cost_discount",
        "pba_cost_discount_percent",
        "pba_cost_freight",
        "pba_cost_tariff",
        "pba_cost_operative",
        "pba_cost_nationalization",
        "pba_cost_freight_percent",
        "pba_cost_tariff_percent",
        "pba_cost_operative_percent",
        "pba_cost_nationalization_percent",
        "standard_price",
        "list_price",
        "cost_currency_id",
    )
    def _compute_pba_final_cost(self):
        icp = self.env["ir.config_parameter"].sudo()
        formula = (
            icp.get_param(
                "pba_costs.final_cost_formula",
                DEFAULT_PBA_FINAL_COST_FORMULA,
            )
            or ""
        ).strip() or DEFAULT_PBA_FINAL_COST_FORMULA
        for template in self:
            ctx = template._pba_final_cost_formula_context()
            try:
                template.pba_final_cost = float(safe_eval(formula, ctx))
            except Exception as err:
                _logger.warning(
                    "pba_costs: error al evaluar la fórmula del costo final %r: %s",
                    formula,
                    err,
                )
                template.pba_final_cost = (
                    (template.pba_last_cost or 0.0)
                    - (template.pba_cost_discount or 0.0)
                    + (template.pba_cost_freight or 0.0)
                    + (template.pba_cost_tariff or 0.0)
                    + (template.pba_cost_operative or 0.0)
                    + (template.pba_cost_nationalization or 0.0)
                )

    @api.depends("pba_final_cost")
    def _compute_pba_session_debug(self):
        try:
            from odoo.http import request

            sess = getattr(request, "session", None)
            dbg = sess and sess.debug
            active = bool(dbg and str(dbg).strip())
        except RuntimeError:
            active = False
        for rec in self:
            rec.pba_session_debug = active

    @api.depends("pba_final_cost")
    def _compute_pba_formula_variables_reference(self):
        text = ", ".join(_pba_final_cost_formula_variable_names())
        for rec in self:
            rec.pba_formula_variables_reference = text

    def _pba_purchase_rate_date_for_display_currency(self):
        self.ensure_one()
        return self._pba_last_purchase_line_conversion_date(
            self._pba_find_last_purchase_order_line(),
        )

    def _pba_convert_cost_amount_to_currency(
        self,
        amount,
        target_currency,
        rate_date=None,
    ):
        self.ensure_one()
        if not target_currency:
            return 0.0
        from_currency = self.cost_currency_id or self.company_id.currency_id
        if not from_currency or from_currency == target_currency:
            return float(amount or 0.0)
        conv_date = (
            rate_date
            if rate_date is not None
            else fields.Date.context_today(self)
        )
        return from_currency._convert(
            float(amount or 0.0),
            target_currency,
            self.company_id,
            conv_date,
            round=True,
        )

    @api.depends(
        "pba_cost_display_currency_id",
        "cost_currency_id",
        "company_id",
        "standard_price",
        "pba_last_cost",
        "pba_final_cost",
        "pba_cost_freight",
        "pba_cost_tariff",
        "pba_cost_operative",
        "pba_cost_nationalization",
    )
    def _compute_pba_costs_display_currency_amounts(self):
        for rec in self:
            ccy = rec.pba_cost_display_currency_id
            if not ccy:
                rec.pba_standard_price_display_ccy = 0.0
                rec.pba_last_cost_display_ccy = 0.0
                rec.pba_final_cost_display_ccy = 0.0
                rec.pba_cost_freight_display_ccy = 0.0
                rec.pba_cost_tariff_display_ccy = 0.0
                rec.pba_cost_operative_display_ccy = 0.0
                rec.pba_cost_nationalization_display_ccy = 0.0
                continue
            rate_date = rec._pba_purchase_rate_date_for_display_currency()
            rec.pba_standard_price_display_ccy = rec._pba_convert_cost_amount_to_currency(
                rec.standard_price,
                ccy,
                rate_date,
            )
            rec.pba_last_cost_display_ccy = rec._pba_convert_cost_amount_to_currency(
                rec.pba_last_cost,
                ccy,
                rate_date,
            )
            rec.pba_final_cost_display_ccy = rec._pba_convert_cost_amount_to_currency(
                rec.pba_final_cost,
                ccy,
                rate_date,
            )
            rec.pba_cost_freight_display_ccy = rec._pba_convert_cost_amount_to_currency(
                rec.pba_cost_freight,
                ccy,
                rate_date,
            )
            rec.pba_cost_tariff_display_ccy = rec._pba_convert_cost_amount_to_currency(
                rec.pba_cost_tariff,
                ccy,
                rate_date,
            )
            rec.pba_cost_operative_display_ccy = rec._pba_convert_cost_amount_to_currency(
                rec.pba_cost_operative,
                ccy,
                rate_date,
            )
            rec.pba_cost_nationalization_display_ccy = (
                rec._pba_convert_cost_amount_to_currency(
                    rec.pba_cost_nationalization,
                    ccy,
                    rate_date,
                )
            )

    @api.depends("pba_final_cost")
    def _compute_pba_final_cost_formula_edit(self):
        icp = self.env["ir.config_parameter"].sudo()
        text = icp.get_param(
            "pba_costs.final_cost_formula",
            DEFAULT_PBA_FINAL_COST_FORMULA,
        )
        for rec in self:
            rec.pba_final_cost_formula_edit = text

    def _inverse_pba_final_cost_formula_edit(self):
        if not self:
            return
        self._pba_assert_formula_edit_group()
        formula = (self[:1].pba_final_cost_formula_edit or "").strip()
        if not formula:
            formula = DEFAULT_PBA_FINAL_COST_FORMULA
        try:
            safe_eval(formula, pba_final_cost_dummy_eval_context())
        except Exception as err:
            raise UserError(_("La fórmula no es válida: %s") % err) from err
        self.env["ir.config_parameter"].sudo().set_param(
            "pba_costs.final_cost_formula",
            formula,
        )
        self.env["product.template"].invalidate_model(
            ["pba_final_cost", "pba_final_cost_formula_edit"]
        )

    def _pba_assert_formula_edit_group(self):
        if not self.env.user.has_group("base.group_no_one"):
            raise UserError(
                _(
                    "Solo los usuarios con el grupo «Características técnicas» pueden editar "
                    "la fórmula global del costo final desde la ficha del producto."
                )
            )

    def _pba_final_cost_formula_context(self):
        self.ensure_one()

        def z(val):
            return float(val or 0.0)

        base = z(self.pba_last_cost)
        discount_pct = z(self.pba_cost_discount_percent)
        discount_amt = z(self.pba_cost_discount)
        base_after_discount = base - discount_amt
        return {
            "pba_last_cost": base,
            "pba_cost_discount": discount_amt,
            "pba_cost_discount_percent": discount_pct,
            "pba_cost_freight": z(self.pba_cost_freight),
            "pba_cost_tariff": z(self.pba_cost_tariff),
            "pba_cost_operative": z(self.pba_cost_operative),
            "pba_cost_nationalization": z(self.pba_cost_nationalization),
            "pba_cost_freight_operation_total": base_after_discount,
            "pba_cost_freight_percent": z(self.pba_cost_freight_percent),
            "pba_cost_tariff_operation_total": base_after_discount,
            "pba_cost_tariff_percent": z(self.pba_cost_tariff_percent),
            "pba_cost_operative_operation_total": base_after_discount,
            "pba_cost_operative_percent": z(self.pba_cost_operative_percent),
            "pba_cost_nationalization_operation_total": base_after_discount,
            "pba_cost_nationalization_percent": z(self.pba_cost_nationalization_percent),
            "standard_price": z(self.standard_price),
            "list_price": z(self.list_price),
        }

    def _pba_invalidate_last_cost(self):
        if not self:
            return
        self.invalidate_recordset(
            [
                "pba_last_cost",
                "pba_cost_discount",
                "pba_cost_freight",
                "pba_cost_tariff",
                "pba_cost_operative",
                "pba_cost_nationalization",
                "pba_final_cost",
                "pba_suggested_list_price",
                "pba_utility_margin_amount",
            ]
        )
        for fname in (
            "pba_cost_discount",
            "pba_cost_freight",
            "pba_cost_tariff",
            "pba_cost_operative",
            "pba_cost_nationalization",
        ):
            self.env.add_to_compute(self._fields[fname], self)

    def _pba_recompute_cost_amounts_from_last_cost(self):
        amount_fields = [
            "pba_cost_discount",
            "pba_cost_freight",
            "pba_cost_tariff",
            "pba_cost_operative",
            "pba_cost_nationalization",
        ]
        for offset in range(0, len(self), 200):
            batch = self[offset : offset + 200]
            batch.invalidate_recordset(["pba_last_cost"] + amount_fields)
            batch._compute_pba_last_cost()
            batch._compute_pba_cost_discount()
            batch._compute_pba_cost_freight()
            batch._compute_pba_cost_tariff()
            batch._compute_pba_cost_operative()
            batch._compute_pba_cost_nationalization()
            batch.flush_recordset(amount_fields)
            batch.invalidate_recordset(
                [
                    "pba_final_cost",
                    "pba_suggested_list_price",
                    "pba_utility_margin_amount",
                ]
            )
        return len(self)

    @api.model
    def pba_recompute_cost_amounts_from_last_cost(self, template_ids=None):
        domain = [
            "|",
            "|",
            "|",
            "|",
            ("pba_cost_discount_percent", "!=", 0.0),
            ("pba_cost_freight_percent", "!=", 0.0),
            ("pba_cost_tariff_percent", "!=", 0.0),
            ("pba_cost_operative_percent", "!=", 0.0),
            ("pba_cost_nationalization_percent", "!=", 0.0),
        ]
        if template_ids:
            records = self.browse(template_ids).exists()
        else:
            records = self.search(domain)
        return records._pba_recompute_cost_amounts_from_last_cost()

    def _pba_invalidate_last_sale_price(self):
        if self:
            self.invalidate_recordset(["pba_last_sale_price"])

    def _pba_cost_types_to_log_on_write(self, vals):
        types = set()
        pct_fields = {pair[1] for _ct, pair in COST_FIELD_GROUPS}
        if any(k in vals for k in pct_fields):
            for cost_type, (_amount_f, pct_f) in COST_FIELD_GROUPS:
                if pct_f in vals:
                    types.add(cost_type)
        if "standard_price" in vals:
            types.update(ct for ct, _pair in COST_FIELD_GROUPS)
        return types

    @api.model_create_multi
    def create(self, vals_list):
        cleaned_list = [_pba_strip_legacy_write_vals(dict(vals)) for vals in vals_list]
        records = super().create(cleaned_list)
        for rec, vals in zip(records, cleaned_list):
            for cost_type, field_names in COST_FIELD_GROUPS:
                if any(fn in vals for fn in field_names):
                    rec._pba_create_cost_history_line(cost_type)
        return records

    def write(self, vals):
        if not self:
            return super().write(vals)
        vals = _pba_strip_legacy_write_vals(vals)
        triggers_by_rec = {rec: rec._pba_cost_types_to_log_on_write(vals) for rec in self}
        res = super().write(vals)
        field_by_type = dict(COST_FIELD_GROUPS)
        for template, cost_types in triggers_by_rec.items():
            for cost_type in cost_types:
                amount_f, pct_f = field_by_type[cost_type]
                if (
                    "standard_price" in vals
                    and pct_f not in vals
                    and not (template[pct_f] or 0.0)
                ):
                    continue
                template._pba_create_cost_history_line(cost_type)
        return res

    def _pba_create_cost_history_line(self, cost_type):
        self.ensure_one()
        field_by_type = dict(COST_FIELD_GROUPS)
        amount_f, pct_f = field_by_type[cost_type]
        self.env["pba.product.cost.history"].create(
            {
                "product_tmpl_id": self.id,
                "cost_type": cost_type,
                "amount": self[amount_f],
                "percent": self[pct_f],
            }
        )

    def _pba_action_cost_history(self, cost_type):
        self.ensure_one()
        return {
            "name": PBA_COST_HISTORY_TITLES.get(cost_type, ""),
            "type": "ir.actions.act_window",
            "res_model": "pba.product.cost.history",
            "view_mode": "list,form",
            "domain": [
                ("product_tmpl_id", "=", self.id),
                ("cost_type", "=", cost_type),
            ],
            "context": {
                "default_product_tmpl_id": self.id,
                "default_cost_type": cost_type,
            },
        }

    def action_pba_cost_history_freight(self):
        return self._pba_action_cost_history("freight")

    def action_pba_cost_history_tariff(self):
        return self._pba_action_cost_history("tariff")

    def action_pba_cost_history_operative(self):
        return self._pba_action_cost_history("operative")

    def action_pba_cost_history_nationalization(self):
        return self._pba_action_cost_history("nationalization")

    def action_pba_last_cost_purchase_traceability(self):
        self.ensure_one()
        variants = self.product_variant_ids
        if not variants:
            return {"type": "ir.actions.act_window_close"}
        return {
            "name": _("Trazabilidad de compras"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.order.line",
            "view_mode": "list,form",
            "views": [
                (
                    self.env.ref(
                        "pba_costs.pba_purchase_line_tree_traceability"
                    ).id,
                    "list",
                ),
                (
                    self.env.ref("purchase.purchase_order_line_form2").id,
                    "form",
                ),
            ],
            "domain": [
                ("product_id", "in", variants.ids),
                ("state", "in", ["purchase", "done"]),
                ("display_type", "=", False),
            ],
        }
