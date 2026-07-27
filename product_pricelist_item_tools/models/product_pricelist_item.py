from odoo import _, api, models
from odoo.exceptions import ValidationError


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    @api.constrains("pricelist_id", "applied_on", "product_tmpl_id", "product_id")
    def _check_unique_product_on_pricelist(self):
        for item in self:
            if not item.pricelist_id:
                continue
            if item.applied_on == "1_product" and item.product_tmpl_id:
                duplicates = self.search_count(
                    [
                        ("id", "!=", item.id),
                        ("pricelist_id", "=", item.pricelist_id.id),
                        ("applied_on", "=", "1_product"),
                        ("product_tmpl_id", "=", item.product_tmpl_id.id),
                    ]
                )
                if duplicates:
                    raise ValidationError(
                        _(
                            "The product %(product)s is already present in pricelist "
                            "%(pricelist)s. Duplicate products are not allowed.",
                            product=item.product_tmpl_id.display_name,
                            pricelist=item.pricelist_id.display_name,
                        )
                    )
            elif item.applied_on == "0_product_variant" and item.product_id:
                duplicates = self.search_count(
                    [
                        ("id", "!=", item.id),
                        ("pricelist_id", "=", item.pricelist_id.id),
                        ("applied_on", "=", "0_product_variant"),
                        ("product_id", "=", item.product_id.id),
                    ]
                )
                if duplicates:
                    raise ValidationError(
                        _(
                            "The variant %(product)s is already present in pricelist "
                            "%(pricelist)s. Duplicate products are not allowed.",
                            product=item.product_id.display_name,
                            pricelist=item.pricelist_id.display_name,
                        )
                    )
