from odoo import _, models
from odoo.exceptions import UserError


class PosSession(models.Model):
    _inherit = "pos.session"

    def _pba_ensure_can_close_session(self):
        seller_sessions = self.filtered(lambda session: session.config_id.pba_seller_pos)
        if seller_sessions:
            raise UserError(
                _(
                    "The Seller Register cannot be closed. It must stay open so "
                    "draft orders can be kept there."
                )
            )

    def action_pos_session_open(self):
        res = super().action_pos_session_open()
        seller_sessions = self.filtered(
            lambda session: session.config_id.pba_seller_pos
            and session.state == "opening_control"
        )
        for session in seller_sessions:
            session.set_opening_control(0, False)
        return res

    def _pba_find_seller_configs(self):
        self.ensure_one()
        trusted_sellers = self.config_id.trusted_config_ids.filtered("pba_seller_pos")
        if trusted_sellers:
            return trusted_sellers
        return self.env["pos.config"].search(
            [
                ("pba_seller_pos", "=", True),
                ("company_id", "=", self.company_id.id),
                ("id", "!=", self.config_id.id),
            ]
        )

    def _pba_get_open_seller_session(self):
        self.ensure_one()
        for config in self._pba_find_seller_configs():
            session = config.current_session_id
            if session and session.state == "opened":
                return session
        return self.env["pos.session"]

    def _pba_move_draft_orders_to_seller_pos(self):
        for session in self:
            if session.config_id.pba_seller_pos:
                continue
            draft_orders = session.get_session_orders().filtered(
                lambda order: order.state == "draft"
            )
            if not draft_orders:
                continue

            empty_orders = draft_orders.filtered(lambda order: not order.lines)
            if empty_orders:
                empty_orders.write({"state": "cancel"})

            orders_to_move = draft_orders - empty_orders
            if not orders_to_move:
                continue

            seller_session = session._pba_get_open_seller_session()
            if not seller_session:
                continue

            orders_to_move.write({"session_id": seller_session.id})
            seller_session.config_id.notify_synchronisation(
                seller_session.id,
                0,
                {"pos.order": orders_to_move.ids},
            )
            session.config_id.notify_synchronisation(
                session.id,
                self.env.context.get("login_number", 0),
                {"pos.order": orders_to_move.ids},
            )

    def _cannot_close_session(self, bank_payment_method_diffs=None):
        if self.config_id.pba_seller_pos:
            return {
                "successful": False,
                "message": _(
                    "The Seller Register cannot be closed. It must stay open so "
                    "draft orders can be kept there."
                ),
                "redirect": False,
            }
        self._pba_move_draft_orders_to_seller_pos()
        result = super()._cannot_close_session(bank_payment_method_diffs)
        if not result:
            return result
        draft_orders = self.get_session_orders().filtered(
            lambda order: order.state == "draft"
        )
        if (
            draft_orders
            and not self.config_id.pba_seller_pos
            and self._pba_find_seller_configs()
            and not self._pba_get_open_seller_session()
        ):
            result = dict(result)
            result["pba_needs_seller_session"] = True
            result["message"] = _(
                "Open the Seller Register so draft orders can be moved there "
                "before closing this session."
            )
        return result

    def action_pos_session_closing_control(
        self,
        balancing_account=False,
        amount_to_balance=0,
        bank_payment_method_diffs=None,
    ):
        self._pba_ensure_can_close_session()
        self._pba_move_draft_orders_to_seller_pos()
        return super().action_pos_session_closing_control(
            balancing_account=balancing_account,
            amount_to_balance=amount_to_balance,
            bank_payment_method_diffs=bank_payment_method_diffs,
        )

    def action_pos_session_close(
        self,
        balancing_account=False,
        amount_to_balance=0,
        bank_payment_method_diffs=None,
    ):
        self._pba_ensure_can_close_session()
        return super().action_pos_session_close(
            balancing_account=balancing_account,
            amount_to_balance=amount_to_balance,
            bank_payment_method_diffs=bank_payment_method_diffs,
        )

    def close_session_from_ui(self, bank_payment_method_diff_pairs=None):
        self._pba_ensure_can_close_session()
        return super().close_session_from_ui(bank_payment_method_diff_pairs)
