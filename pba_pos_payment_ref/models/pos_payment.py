from odoo import api, models


class PosPayment(models.Model):
    _inherit = "pos.payment"

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = list(super()._load_pos_data_fields(config_id))
        if fields_list and "payment_ref_no" not in fields_list:
            fields_list.append("payment_ref_no")
        return fields_list

    def _create_payment_moves(self, is_reverse=False):
        result = super()._create_payment_moves(is_reverse=is_reverse)
        for payment in self.filtered(
            lambda p: p.payment_method_id.type == "bank"
            and p.payment_ref_no
            and p.account_move_id
        ):
            payment.account_move_id.write({"ref": payment.payment_ref_no})
        return result
