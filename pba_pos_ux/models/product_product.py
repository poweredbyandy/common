from odoo import _, api, exceptions, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def pba_get_pos_currency_prices(self, product_ids, config_id):
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise exceptions.AccessError(
                _("You are not allowed to load POS product prices.")
            )
        config = self.env["pos.config"].browse(config_id).exists()
        if not config:
            raise exceptions.UserError(_("POS configuration not found."))
        config.check_access("read")
        product_ids = list(dict.fromkeys(product_ids))[:30]
        products = self._load_product_with_domain(
            [
                ("id", "in", product_ids),
                ("available_in_pos", "=", True),
                ("sale_ok", "=", True),
            ],
            config.id,
        )
        self._process_pos_ui_product_product(products, config)
        return {
            product["id"]: {
                "lst_price": product["lst_price"],
                "standard_price": product["standard_price"],
            }
            for product in products
        }
