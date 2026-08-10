from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    pba_seller_pos = fields.Boolean(
        string="Seller Register",
        help="Seller Point of Sale without cash control. Sessions stay open, "
        "closing is disabled, and settings can be changed while the session "
        "is open.",
    )

    @api.depends("payment_method_ids", "pba_seller_pos")
    def _compute_cash_control(self):
        super()._compute_cash_control()
        for config in self:
            if config.pba_seller_pos:
                config.cash_control = False

    def _get_forbidden_change_fields(self):
        if self and all(self.mapped("pba_seller_pos")):
            return []
        return super()._get_forbidden_change_fields()

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = list(super()._load_pos_data_fields(config_id))
        if fields_list and "pba_seller_pos" not in fields_list:
            fields_list.append("pba_seller_pos")
        return fields_list
