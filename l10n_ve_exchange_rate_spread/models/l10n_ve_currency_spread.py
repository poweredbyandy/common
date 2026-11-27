# Copyright 2026 Anderson Armeya
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_round


class L10nVeCurrencySpread(models.Model):
    _name = "l10n.ve.currency.spread"
    _description = "Comparación de spread de tasas de cambio"
    _order = "sequence, id"
    _check_company_domain = models.check_company_domain_parent_of

    name = fields.Char(
        string="Comparación",
        compute="_compute_name",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    from_currency_id = fields.Many2one(
        "res.currency",
        string="Desde (referencia)",
        required=True,
        index=True,
        help="Moneda base del spread. Ejemplo: USD (tasa oficial BCV).",
    )
    to_currency_id = fields.Many2one(
        "res.currency",
        string="Hacia (comparada)",
        required=True,
        index=True,
        help="Moneda comparada contra la de referencia. Ejemplo: USDT.",
    )
    from_rate = fields.Float(
        string="Tasa Desde",
        compute="_compute_spread",
        digits=0,
        help="Cantidad de la moneda de la compañía por 1 unidad de la "
        "moneda de referencia.",
    )
    to_rate = fields.Float(
        string="Tasa Hacia",
        compute="_compute_spread",
        digits=0,
        help="Cantidad de la moneda de la compañía por 1 unidad de la "
        "moneda comparada.",
    )
    spread = fields.Float(
        string="Spread %",
        compute="_compute_spread",
        digits=(16, 2),
        help="Diferencia porcentual de la tasa comparada respecto a la "
        "tasa de referencia: (Hacia − Desde) / Desde × 100.",
    )
    ratio = fields.Float(
        string="Relación",
        compute="_compute_spread",
        digits=(16, 4),
        help="Cuántas unidades de la moneda comparada equivalen a 1 "
        "unidad de la moneda de referencia.",
    )
    has_rate = fields.Boolean(
        string="Con tasa",
        compute="_compute_spread",
        help="Indica si ambas monedas tienen tasa vigente contra la "
        "moneda de la compañía.",
    )

    _sql_constraints = [
        (
            "unique_pair_per_company",
            "unique (company_id, from_currency_id, to_currency_id)",
            "Ya existe esta comparación de monedas para la compañía.",
        ),
    ]

    @api.depends("from_currency_id", "to_currency_id")
    def _compute_name(self):
        for rec in self:
            if rec.from_currency_id and rec.to_currency_id:
                rec.name = _(
                    "%(from_name)s → %(to_name)s",
                    from_name=rec.from_currency_id.name,
                    to_name=rec.to_currency_id.name,
                )
            else:
                rec.name = ""

    @api.depends(
        "company_id",
        "company_id.currency_id",
        "from_currency_id",
        "to_currency_id",
        "from_currency_id.rate_ids.rate",
        "to_currency_id.rate_ids.rate",
    )
    def _compute_spread(self):
        for rec in self:
            (
                rec.from_rate,
                rec.to_rate,
                rec.spread,
                rec.ratio,
                rec.has_rate,
            ) = rec._compute_rates()

    def _compute_rates(self):
        self.ensure_one()
        company = self.company_id or self.env.company
        from_currency = self.from_currency_id.with_company(company)
        to_currency = self.to_currency_id.with_company(company)
        if not from_currency or not to_currency:
            return 0.0, 0.0, 0.0, 0.0, False
        from_rate = from_currency.inverse_rate
        to_rate = to_currency.inverse_rate
        if not from_rate or not to_rate:
            return from_rate, to_rate, 0.0, 0.0, False
        spread = (to_rate - from_rate) / from_rate * 100.0
        ratio = from_rate / to_rate
        return from_rate, to_rate, spread, ratio, True

    @api.constrains("from_currency_id", "to_currency_id")
    def _check_currencies(self):
        for rec in self:
            if (
                rec.from_currency_id
                and rec.from_currency_id == rec.to_currency_id
            ):
                raise ValidationError(
                    _(
                        "Las monedas \"Desde\" y \"Hacia\" deben ser "
                        "diferentes."
                    )
                )

    def get_spread_tooltip_data(self):
        """Datos serializables para el tooltip de tasas de la navbar."""
        company_currency = self.env.company.currency_id
        company_symbol = company_currency.symbol if company_currency else ""
        result = []
        for rec in self:
            from_currency = rec.from_currency_id
            to_currency = rec.to_currency_id
            spread, ratio = 0.0, 0.0
            if rec.has_rate:
                spread = float_round(rec.spread, precision_digits=2)
                ratio = float_round(
                    rec.ratio,
                    precision_digits=max(to_currency.decimal_places, 4),
                )
            result.append(
                {
                    "label": rec.name,
                    "from_name": from_currency.name,
                    "to_name": to_currency.name,
                    "from_rate": float_round(
                        rec.from_rate,
                        precision_digits=from_currency.decimal_places,
                    ),
                    "to_rate": float_round(
                        rec.to_rate,
                        precision_digits=to_currency.decimal_places,
                    ),
                    "spread": spread,
                    "ratio": ratio,
                    "positive": rec.spread > 0,
                    "has_rate": rec.has_rate,
                    "company_currency_symbol": company_symbol,
                }
            )
        return result
