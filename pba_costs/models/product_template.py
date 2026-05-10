import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

DEFAULT_PBA_FINAL_COST_FORMULA = (
    "pba_last_cost + pba_cost_freight + pba_cost_tariff + "
    "pba_cost_operative + pba_cost_nationalization"
)


def _pba_final_cost_formula_variable_names():
    return (
        "pba_last_cost",
        "pba_cost_freight",
        "pba_cost_tariff",
        "pba_cost_operative",
        "pba_cost_nationalization",
        "pba_cost_freight_operation_total",
        "pba_cost_freight_percent",
        "pba_cost_tariff_operation_total",
        "pba_cost_tariff_percent",
        "pba_cost_operative_operation_total",
        "pba_cost_operative_percent",
        "pba_cost_nationalization_operation_total",
        "pba_cost_nationalization_percent",
        "standard_price",
        "list_price",
    )


def pba_final_cost_dummy_eval_context():
    return {k: 1.0 for k in _pba_final_cost_formula_variable_names()}


PBA_COST_IMPORTE_HELP = (
    "Calculado: costo promedio del producto (standard_price) × % aplicado."
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

    pba_final_cost_formula_edit = fields.Text(
        string="Fórmula global del costo final",
        compute="_compute_pba_final_cost_formula_edit",
        inverse="_inverse_pba_final_cost_formula_edit",
        help="Misma expresión global para todos los productos. Visible y editable en el producto solo "
        "para usuarios con el grupo Características técnicas (base.group_no_one). Ver ayuda en Ajustes ▸ PBA Costos.",
    )

    @api.depends(
        "product_variant_ids",
        "cost_currency_id",
        "standard_price",
    )
    def _compute_pba_last_cost(self):
        Pol = self.env["purchase.order.line"]
        for template in self:
            fallback = template.standard_price or 0.0
            variants = template.product_variant_ids
            if not variants:
                template.pba_last_cost = fallback
                continue
            line = Pol.search(
                [
                    ("product_id", "in", variants.ids),
                    ("state", "in", ["purchase", "done"]),
                    ("display_type", "=", False),
                ],
                order="date_approve desc, date_order desc, id desc",
                limit=1,
            )
            if not line:
                template.pba_last_cost = fallback
                continue
            price_uom = line.product_uom._compute_price(
                line.price_unit_discounted,
                line.product_id.uom_id,
            )
            line_dt = line.date_approve or line.date_order
            if line_dt:
                date = line_dt.date() if hasattr(line_dt, "date") else line_dt
            else:
                date = fields.Date.context_today(line)
            to_currency = template.cost_currency_id or line.company_id.currency_id
            template.pba_last_cost = line.currency_id._convert(
                price_uom,
                to_currency,
                line.company_id,
                date,
                round=True,
            )

    @api.depends("standard_price", "pba_cost_freight_percent")
    def _compute_pba_cost_freight(self):
        for rec in self:
            base = rec.standard_price or 0.0
            pct = rec.pba_cost_freight_percent or 0.0
            rec.pba_cost_freight = base * pct

    @api.depends("standard_price", "pba_cost_tariff_percent")
    def _compute_pba_cost_tariff(self):
        for rec in self:
            base = rec.standard_price or 0.0
            pct = rec.pba_cost_tariff_percent or 0.0
            rec.pba_cost_tariff = base * pct

    @api.depends("standard_price", "pba_cost_operative_percent")
    def _compute_pba_cost_operative(self):
        for rec in self:
            base = rec.standard_price or 0.0
            pct = rec.pba_cost_operative_percent or 0.0
            rec.pba_cost_operative = base * pct

    @api.depends("standard_price", "pba_cost_nationalization_percent")
    def _compute_pba_cost_nationalization(self):
        for rec in self:
            base = rec.standard_price or 0.0
            pct = rec.pba_cost_nationalization_percent or 0.0
            rec.pba_cost_nationalization = base * pct

    @api.depends(
        "pba_last_cost",
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

        base = z(self.standard_price)
        return {
            "pba_last_cost": z(self.pba_last_cost),
            "pba_cost_freight": z(self.pba_cost_freight),
            "pba_cost_tariff": z(self.pba_cost_tariff),
            "pba_cost_operative": z(self.pba_cost_operative),
            "pba_cost_nationalization": z(self.pba_cost_nationalization),
            "pba_cost_freight_operation_total": base,
            "pba_cost_freight_percent": z(self.pba_cost_freight_percent),
            "pba_cost_tariff_operation_total": base,
            "pba_cost_tariff_percent": z(self.pba_cost_tariff_percent),
            "pba_cost_operative_operation_total": base,
            "pba_cost_operative_percent": z(self.pba_cost_operative_percent),
            "pba_cost_nationalization_operation_total": base,
            "pba_cost_nationalization_percent": z(self.pba_cost_nationalization_percent),
            "standard_price": base,
            "list_price": z(self.list_price),
        }

    def _pba_invalidate_last_cost(self):
        if self:
            self.invalidate_recordset(["pba_last_cost", "pba_final_cost"])

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
