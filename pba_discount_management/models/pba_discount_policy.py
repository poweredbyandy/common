from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class PbaDiscountPolicy(models.AbstractModel):
    _name = "pba.discount.policy"
    _description = "Discount limits policy"

    def _pba_has_unlimited_discount(self):
        return self.env.user.has_group(
            "pba_discount_management.group_pba_discount_unlimited"
        )

    def _pba_has_global_discount_group(self):
        return self.env.user.has_group(
            "pba_discount_management.group_pba_global_sale_invoice_discount"
        )

    def _pba_effective_max_discount_percent(self, company, partner):
        company = company or self.env.company
        c = company.pba_max_discount_percent or 0.0
        commercial = partner.commercial_partner_id if partner else self.env["res.partner"]
        p = (commercial.pba_max_discount_percent or 0.0) if commercial else 0.0
        return max(c, p)

    def _pba_raise_if_discount_over_limit(self, percent_value, company, partner):
        if self._pba_has_unlimited_discount():
            return
        limit = self._pba_effective_max_discount_percent(company, partner)
        prec = self.env["decimal.precision"].precision_get("Discount")
        if float_compare(percent_value, limit, precision_digits=prec) > 0:
            raise UserError(
                _(
                    "The discount (%(value)s%%) exceeds the allowed maximum (%(limit)s%%) for this "
                    "company or customer.",
                    value=percent_value,
                    limit=limit,
                )
            )

    def _pba_raise_if_ratio_over_limit(self, ratio_0_1, company, partner):
        if self._pba_has_unlimited_discount():
            return
        self._pba_raise_if_discount_over_limit((ratio_0_1 or 0.0) * 100.0, company, partner)

    def _pba_require_global_discount_rights(self):
        if self._pba_has_unlimited_discount() or self._pba_has_global_discount_group():
            return
        raise UserError(
            _(
                "You are not allowed to use the order discount wizard. "
                "Ask an administrator to grant global discount rights on sales and invoices."
            )
        )
