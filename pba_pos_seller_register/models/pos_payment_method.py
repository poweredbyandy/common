from odoo import models


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    def _compute_open_session_ids(self):
        super()._compute_open_session_ids()
        for payment_method in self:
            payment_method.open_session_ids = payment_method.open_session_ids.filtered(
                lambda session: not session.config_id.pba_seller_pos
            )
