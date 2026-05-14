from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResCurrencyRate(models.Model):
    _inherit = "res.currency.rate"

    reference_usd_visible = fields.Boolean(
        compute="_compute_reference_usd_visible",
    )
    foreign_per_usd = fields.Float(
        digits=(16, 6),
        string="Moneda por 1 USD",
        help="Cantidad de unidades de esta moneda equivalentes a 1 USD "
        "(por ejemplo JPY por dólar). Se calcula la tasa en la moneda de la compañía "
        "usando la tasa USD vigente en la misma fecha.",
    )

    @api.depends("currency_id", "company_id", "company_id.currency_id")
    def _compute_reference_usd_visible(self):
        usd = self.env.ref("base.USD", raise_if_not_found=False)
        for rec in self:
            comp = rec.company_id or self.env.company
            root = comp.root_id
            ccy = root.currency_id
            rec.reference_usd_visible = bool(
                usd
                and rec.currency_id
                and rec.currency_id != usd
                and ccy
                and ccy != usd
            )

    def _usd_inverse_company_rate(self, company, rate_date):
        usd = self.env.ref("base.USD", raise_if_not_found=False)
        if not usd:
            return 0.0
        root = company.root_id
        domain = [
            ("currency_id", "=", usd.id),
            ("name", "<=", rate_date),
            "|",
            ("company_id", "=", False),
            ("company_id", "=", root.id),
        ]
        line = self.search(domain, order="name desc, company_id desc", limit=1)
        if not line:
            return 0.0
        return line.inverse_company_rate or 0.0

    @api.model
    def get_foreign_per_usd_at_date(self, company, rate_date, currency):
        usd = self.env.ref("base.USD", raise_if_not_found=False)
        if not usd or not currency or currency == usd:
            return 0.0
        root = company.root_id
        if root.currency_id == usd:
            return 0.0
        if not rate_date:
            rate_date = fields.Date.context_today(self)
        domain = [
            ("currency_id", "=", currency.id),
            ("name", "<=", rate_date),
            "|",
            ("company_id", "=", False),
            ("company_id", "=", root.id),
        ]
        line = self.search(domain, order="name desc, company_id desc", limit=1)
        if not line:
            return 0.0
        if line.foreign_per_usd:
            return line.foreign_per_usd
        usd_inv = self._usd_inverse_company_rate(root, rate_date)
        inv = line.inverse_company_rate or 0.0
        if not usd_inv or not inv:
            return 0.0
        return usd_inv / inv

    def _vals_apply_foreign_per_usd(self, vals, record=None):
        if not vals.get("foreign_per_usd"):
            return vals
        vals = dict(vals)
        currency = None
        if vals.get("currency_id"):
            currency = self.env["res.currency"].browse(vals["currency_id"])
        elif record:
            currency = record.currency_id
        if not currency:
            return vals
        usd = self.env.ref("base.USD", raise_if_not_found=False)
        if not usd or currency == usd:
            vals.pop("foreign_per_usd", None)
            return vals
        if record and record.company_id:
            company = record.company_id
        elif vals.get("company_id"):
            company = self.env["res.company"].browse(vals["company_id"])
        else:
            company = self.env.company
        root = company.root_id
        if root.currency_id == usd:
            vals.pop("foreign_per_usd", None)
            return vals
        rate_date = vals.get("name")
        if record and not rate_date:
            rate_date = record.name
        if not rate_date:
            rate_date = fields.Date.context_today(self)
        n = vals["foreign_per_usd"]
        if n <= 0:
            raise UserError(_("La cantidad 'Moneda por 1 USD' debe ser mayor que cero."))
        usd_inv = self._usd_inverse_company_rate(root, rate_date)
        if not usd_inv:
            raise UserError(
                _("No hay tasa de USD frente a la moneda de la compañía para la fecha %s.")
                % rate_date
            )
        vals["inverse_company_rate"] = usd_inv / n
        if "company_rate" in vals:
            del vals["company_rate"]
        if "rate" in vals:
            del vals["rate"]
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        out = []
        for vals in vals_list:
            out.append(self._vals_apply_foreign_per_usd(vals))
        return super().create(out)

    def write(self, vals):
        if not vals.get("foreign_per_usd"):
            return super().write(vals)
        if len(self) > 1:
            raise UserError(
                _("No puede aplicar cotización en USD a varias líneas a la vez; guarde una fila cada vez.")
            )
        merged = self._vals_apply_foreign_per_usd(dict(vals), record=self)
        return super().write(merged)

    @api.onchange("foreign_per_usd", "name", "company_id", "currency_id")
    def _onchange_foreign_per_usd(self):
        if not self.foreign_per_usd or not self.reference_usd_visible:
            return
        if self.foreign_per_usd <= 0:
            return {
                "warning": {
                    "title": _("Valor no válido"),
                    "message": _("La cantidad 'Moneda por 1 USD' debe ser mayor que cero."),
                }
            }
        company = self.company_id or self.env.company
        usd_inv = self._usd_inverse_company_rate(company.root_id, self.name)
        if not usd_inv:
            return {
                "warning": {
                    "title": _("Sin tasa USD"),
                    "message": _(
                        "No hay tasa de USD frente a la moneda de la compañía para la fecha indicada."
                    ),
                }
            }
        self.inverse_company_rate = usd_inv / self.foreign_per_usd
