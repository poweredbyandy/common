from odoo import api, fields, models
from odoo.osv import expression


class ProductTemplate(models.Model):
    _inherit = "product.template"

    internal_code = fields.Char(
        string="Código interno",
        help="Identificador interno adicional del producto, distinto de la referencia interna de variante.",
    )

    @api.depends("name", "default_code", "internal_code")
    def _compute_display_name(self):
        super()._compute_display_name()
        for template in self:
            if not template.name:
                continue
            if not self._context.get("display_default_code", True):
                continue
            codes = []
            if template.default_code:
                codes.append(template.default_code)
            if template.internal_code:
                codes.append(template.internal_code)
            if codes:
                template.display_name = f"[{' | '.join(codes)}] {template.name}"

    @api.model
    def _search_display_name(self, operator, value):
        domain = super()._search_display_name(operator, value)
        if operator not in expression.NEGATIVE_TERM_OPERATORS:
            ic_domain = [("internal_code", operator, value)]
            if domain:
                return expression.OR([domain, ic_domain])
            return ic_domain
        ic_domain = [("internal_code", operator, value)]
        return expression.AND([domain, ic_domain])

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        self_obj = self
        if "search_product_product" not in self.env.context and any(
            term[0] == "id" for term in (args or [])
        ):
            self_obj = self_obj.with_context(search_product_product=False)
        results = super(ProductTemplate, self_obj).name_search(name, args, operator, limit)
        if not results and name:
            domain = args or []
            ic_domain = expression.AND([domain, [("internal_code", operator, name)]])
            templates = self_obj.search(ic_domain, limit=limit)
            if templates:
                results = [(t.id, t.display_name) for t in templates]
        return results
