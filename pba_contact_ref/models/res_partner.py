import re

from odoo import api, models
from odoo.osv import expression


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _pba_contact_ref_use_ve_trading_display(self):
        if not self.env["res.partner"].browse()._l10n_ve_fiscal_locks_apply():
            return False
        ctx = self.env.context
        if ctx.get("l10n_ve_display_name_vat_first"):
            return True
        if ctx.get("res_partner_search_mode") in ("customer", "supplier"):
            return True
        return False

    @api.depends(
        "complete_name",
        "email",
        "vat",
        "ref",
        "state_id",
        "country_id",
        "commercial_company_name",
    )
    @api.depends_context(
        "show_address",
        "partner_show_db_id",
        "address_inline",
        "show_email",
        "show_vat",
        "lang",
        "l10n_ve_display_name_vat_first",
        "res_partner_search_mode",
    )
    def _compute_display_name(self):
        if not self._pba_contact_ref_use_ve_trading_display():
            return super()._compute_display_name()
        for partner in self:
            name = partner.with_context(lang=self.env.lang)._get_complete_name()
            if partner._context.get("show_address"):
                name = name + "\n" + partner._display_address(without_company=True)
            name = re.sub(r"\s+\n", "\n", name)
            if partner._context.get("partner_show_db_id"):
                name = f"{name} ({partner.id})"
            if partner._context.get("address_inline"):
                splitted_names = name.split("\n")
                name = ", ".join([n for n in splitted_names if n.strip()])
            if partner._context.get("show_email") and partner.email:
                name = f"{name} <{partner.email}>"
            vat = (partner.vat or "").strip()
            if vat == "/":
                vat = ""
            ref = (partner.ref or "").strip()
            segments = []
            if ref:
                segments.append(f"[{ref}]")
            if vat:
                segments.append(vat)
            core = name.strip()
            if core:
                segments.append(core)
            partner.display_name = " ".join(segments).strip()

    @api.model
    def _search_display_name(self, operator, value):
        domain = super()._search_display_name(operator, value)
        if not self._pba_contact_ref_use_ve_trading_display():
            return domain
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            return domain
        if not value or not str(value).strip():
            return domain
        ref_term = str(value).strip()
        return expression.OR([domain, [("ref", "ilike", ref_term)]])
