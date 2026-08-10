from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def pba_get_pos_currency_prices(self, product_ids, config_id):
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise AccessError(_("You are not allowed to load POS product prices."))
        config = self.env["pos.config"].browse(config_id).exists()
        if not config:
            raise UserError(_("POS configuration not found."))
        config.check_access("read")
        product_ids = list(dict.fromkeys(product_ids))[:30]
        products = self.search(
            [
                ("id", "in", product_ids),
                ("available_in_pos", "=", True),
                ("sale_ok", "=", True),
            ]
        )
        company_currency = config.company_id.currency_id
        pos_currency = config.currency_id
        conversion_date = fields.Date.today()
        return {
            product.id: {
                "lst_price": company_currency._convert(
                    product.lst_price,
                    pos_currency,
                    config.company_id,
                    conversion_date,
                ),
                "standard_price": company_currency._convert(
                    product.standard_price,
                    pos_currency,
                    config.company_id,
                    conversion_date,
                ),
            }
            for product in products
        }
