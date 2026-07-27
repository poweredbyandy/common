from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    pba_sale_order_as_invoice_ids = fields.One2many(
        comodel_name="sale.order",
        inverse_name="partner_invoice_id",
        string="Sale Orders as Invoice Address",
    )
    pba_sale_order_as_shipping_ids = fields.One2many(
        comodel_name="sale.order",
        inverse_name="partner_shipping_id",
        string="Sale Orders as Shipping Address",
    )

    def _pba_prepare_custom_seller_vals(self, vals):
        user = self.env.user
        if not user._pba_is_limited_custom_seller():
            return vals
        vals = dict(vals)
        vals["user_id"] = user.id
        default_pricelist = user._pba_custom_seller_default_pricelist()
        if default_pricelist:
            vals["property_product_pricelist"] = default_pricelist.id
        for command in vals.get("child_ids") or []:
            if command[0] == fields.Command.CREATE:
                child_vals = command[2]
                child_vals["user_id"] = user.id
                if default_pricelist:
                    child_vals["property_product_pricelist"] = default_pricelist.id
        return vals

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        user = self.env.user
        if not user._pba_is_limited_custom_seller():
            return values
        if "user_id" in fields_list and not values.get("user_id"):
            values["user_id"] = user.id
        if "property_product_pricelist" in fields_list:
            default_pricelist = user._pba_custom_seller_default_pricelist()
            if default_pricelist:
                values["property_product_pricelist"] = default_pricelist.id
        return values

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.user._pba_is_limited_custom_seller():
            vals_list = [
                self._pba_prepare_custom_seller_vals(vals) for vals in vals_list
            ]
        return super().create(vals_list)
