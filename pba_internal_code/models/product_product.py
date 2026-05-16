from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools.misc import unique


class ProductProduct(models.Model):
    _inherit = "product.product"

    internal_code = fields.Char(
        related="product_tmpl_id.internal_code",
        string="Código interno",
        readonly=False,
        store=True,
        index=True,
    )

    @api.depends(
        "name",
        "default_code",
        "product_tmpl_id",
        "product_tmpl_id.internal_code",
        "internal_code",
    )
    @api.depends_context("display_default_code", "seller_id", "company_id", "partner_id", "lang")
    def _compute_display_name(self):

        def get_display_name(name, code, internal_code):
            if self._context.get("display_default_code", True):
                codes = []
                if code:
                    codes.append(code)
                if internal_code:
                    codes.append(internal_code)
                if codes:
                    code_string = " | ".join(codes)
                    return f"[{code_string}] {name}"
            return name

        partner_id = self._context.get("partner_id")
        if partner_id:
            partner_ids = [
                partner_id,
                self.env["res.partner"].browse(partner_id).commercial_partner_id.id,
            ]
        else:
            partner_ids = []
        company_id = self.env.context.get("company_id")

        self.check_access("read")

        product_template_ids = self.sudo().product_tmpl_id.ids

        if partner_ids:
            supplier_info = self.env["product.supplierinfo"].sudo().search_fetch(
                [
                    ("product_tmpl_id", "in", product_template_ids),
                    ("partner_id", "in", partner_ids),
                ],
                ["product_tmpl_id", "product_id", "company_id", "product_name", "product_code"],
            )
            supplier_info_by_template = {}
            for r in supplier_info:
                supplier_info_by_template.setdefault(r.product_tmpl_id, []).append(r)

        for product in self.sudo():
            variant = product.product_template_attribute_value_ids._get_combination_name()

            name = variant and "%s (%s)" % (product.name, variant) or product.name
            sellers = self.env["product.supplierinfo"].sudo().browse(self.env.context.get("seller_id")) or []
            if not sellers and partner_ids:
                product_supplier_info = supplier_info_by_template.get(product.product_tmpl_id, [])
                sellers = [x for x in product_supplier_info if x.product_id and x.product_id == product]
                if not sellers:
                    sellers = [x for x in product_supplier_info if not x.product_id]
                if company_id:
                    sellers = [x for x in sellers if x.company_id.id in [company_id, False]]
            internal_code = product.product_tmpl_id.internal_code
            if sellers:
                temp = []
                for s in sellers:
                    seller_variant = (
                        s.product_name
                        and (variant and "%s (%s)" % (s.product_name, variant) or s.product_name)
                        or False
                    )
                    temp.append(
                        get_display_name(
                            seller_variant or name,
                            s.product_code or product.default_code,
                            internal_code,
                        )
                    )

                product.display_name = ", ".join(unique(temp))
            else:
                product.display_name = get_display_name(name, product.default_code, internal_code)

    @api.model
    def _search_display_name(self, operator, value):
        domain = super()._search_display_name(operator, value)
        if operator not in expression.NEGATIVE_TERM_OPERATORS:
            ic_domain = [("product_tmpl_id.internal_code", operator, value)]
            if domain:
                return expression.OR([domain, ic_domain])
            return ic_domain
        ic_domain = [("product_tmpl_id.internal_code", operator, value)]
        return expression.AND([domain, ic_domain])

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        results = super().name_search(name, args, operator, limit)
        if not results and name:
            domain = args or []
            ic_domain = expression.AND([domain, [("product_tmpl_id.internal_code", operator, name)]])
            products = self.search(ic_domain, limit=limit)
            if products:
                results = [(product.id, product.display_name) for product in products]
        return results
