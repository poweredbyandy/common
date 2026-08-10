from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    pba_seller_id = fields.Many2one(
        "hr.employee",
        string="Seller",
        help="Employee who created the order. Kept even if another cashier finishes the payment.",
        index=True,
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        if result and "pba_seller_id" not in result:
            return list(result) + ["pba_seller_id"]
        return result

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        seller_user = self.pba_seller_id.user_id
        if seller_user:
            vals["invoice_user_id"] = seller_user.id
        return vals
