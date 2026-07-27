from odoo import api, models
from odoo.osv import expression


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        if not self.env.context.get("pba_skip_product_restrict"):
            restrict = self.env.user._pba_custom_seller_allowed_template_domain()
            if restrict is not None:
                domain = expression.AND([domain or [], restrict])
        return super()._search(domain, offset=offset, limit=limit, order=order)

    def _compute_quantities(self):
        super()._compute_quantities()
        if not self.env.user._pba_can_see_stock_qty():
            self.qty_available = 0.0
            self.virtual_available = 0.0
            self.incoming_qty = 0.0
            self.outgoing_qty = 0.0
