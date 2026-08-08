from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

PBA_LOCK_DURATION_SECONDS = 30
PBA_LOCK_FIELDS = (
    "pba_lock_device_token",
    "pba_lock_owner_name",
    "pba_lock_owner_user_id",
    "pba_lock_owner_employee_id",
    "pba_lock_expire",
)


class PosOrder(models.Model):
    _inherit = "pos.order"

    pba_lock_device_token = fields.Char(copy=False)
    pba_lock_owner_name = fields.Char(copy=False)
    pba_lock_owner_user_id = fields.Integer(copy=False)
    pba_lock_owner_employee_id = fields.Integer(copy=False)
    pba_lock_expire = fields.Datetime(copy=False)

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        if not fields_list:
            return fields_list
        for name in PBA_LOCK_FIELDS:
            if name not in fields_list:
                fields_list.append(name)
        return fields_list

    def _pba_lock_is_active(self):
        self.ensure_one()
        return bool(
            self.pba_lock_device_token
            and self.pba_lock_expire
            and self.pba_lock_expire > fields.Datetime.now()
        )

    def _pba_lock_clear_vals(self):
        return {
            "pba_lock_device_token": False,
            "pba_lock_owner_name": False,
            "pba_lock_owner_user_id": False,
            "pba_lock_owner_employee_id": False,
            "pba_lock_expire": False,
        }

    def _pba_lock_vals(
        self, device_token, owner_name, owner_user_id=False, owner_employee_id=False
    ):
        return {
            "pba_lock_device_token": device_token,
            "pba_lock_owner_name": owner_name,
            "pba_lock_owner_user_id": owner_user_id or False,
            "pba_lock_owner_employee_id": owner_employee_id or False,
            "pba_lock_expire": fields.Datetime.now()
            + timedelta(seconds=PBA_LOCK_DURATION_SECONDS),
        }

    def _pba_lock_read_payload(self):
        self.ensure_one()
        return self.read(["id", "state", *PBA_LOCK_FIELDS], load=False)

    def _pba_notify_lock_change(self):
        for order in self:
            session = order.session_id
            if not order.config_id or not session:
                continue
            order.config_id.notify_synchronisation(
                session.id,
                self.env.context.get("login_number", 0),
                {"pos.order": [order.id]},
            )

    def _pba_lock_busy_result(self):
        self.ensure_one()
        return {
            "success": False,
            "reason": "locked",
            "owner_name": self.pba_lock_owner_name or _("another device"),
            "order": self._pba_lock_read_payload(),
        }

    def _pba_lock_processed_result(self):
        self.ensure_one()
        return {
            "success": False,
            "reason": "processed",
            "owner_name": False,
            "order": self._pba_lock_read_payload(),
        }

    def _pba_lock_success_result(self):
        self.ensure_one()
        return {
            "success": True,
            "reason": False,
            "owner_name": self.pba_lock_owner_name or False,
            "order": self._pba_lock_read_payload(),
        }

    def _pba_get_locked_order(self, order_id):
        if not order_id:
            raise UserError(_("Missing order."))
        self.env.cr.execute(
            "SELECT id FROM pos_order WHERE id = %s FOR UPDATE",
            (order_id,),
        )
        order = self.browse(order_id).exists()
        if not order:
            raise UserError(_("Order not found."))
        return order

    def _pba_check_sync_lock(self, device_token):
        self.ensure_one()
        if self._pba_lock_is_active() and self.pba_lock_device_token != device_token:
            raise UserError(
                _(
                    "Order %(order)s is being edited by %(owner)s.",
                    order=self.pos_reference or self.name,
                    owner=self.pba_lock_owner_name or _("another device"),
                )
            )

    @api.model
    def _pba_strip_lock_fields(self, orders):
        for order in orders or []:
            for field_name in PBA_LOCK_FIELDS:
                order.pop(field_name, None)

    @api.model
    def pba_get_order_locks(self, order_ids):
        orders = self.browse(order_ids).exists()
        return {
            "success": True,
            "order": orders.read(["id", "state", *PBA_LOCK_FIELDS], load=False),
        }

    @api.model
    def pba_acquire_order_lock(
        self,
        order_id,
        device_token,
        owner_name,
        owner_user_id=False,
        owner_employee_id=False,
    ):
        if not device_token:
            raise UserError(_("Missing device token."))
        order = self._pba_get_locked_order(order_id)
        if order.state != "draft":
            return order._pba_lock_processed_result()
        if order._pba_lock_is_active() and order.pba_lock_device_token != device_token:
            return order._pba_lock_busy_result()
        order.write(
            order._pba_lock_vals(
                device_token,
                owner_name or self.env.user.name,
                owner_user_id=owner_user_id or self.env.user.id,
                owner_employee_id=owner_employee_id,
            )
        )
        order._pba_notify_lock_change()
        return order._pba_lock_success_result()

    @api.model
    def pba_renew_order_lock(self, order_id, device_token):
        if not device_token:
            raise UserError(_("Missing device token."))
        order = self._pba_get_locked_order(order_id)
        if order.state != "draft":
            return order._pba_lock_processed_result()
        if (
            not order._pba_lock_is_active()
            or order.pba_lock_device_token != device_token
        ):
            return order._pba_lock_busy_result()
        order.write(
            {
                "pba_lock_expire": fields.Datetime.now()
                + timedelta(seconds=PBA_LOCK_DURATION_SECONDS),
            }
        )
        return order._pba_lock_success_result()

    @api.model
    def pba_release_order_lock(self, order_id, device_token):
        if not device_token:
            raise UserError(_("Missing device token."))
        order = self._pba_get_locked_order(order_id)
        if (
            order._pba_lock_is_active()
            and order.pba_lock_device_token
            and order.pba_lock_device_token != device_token
        ):
            return order._pba_lock_busy_result()
        order.write(order._pba_lock_clear_vals())
        order._pba_notify_lock_change()
        return order._pba_lock_success_result()

    @api.model
    def sync_from_ui(self, orders):
        self._pba_strip_lock_fields(orders)
        device_token = self.env.context.get("pba_device_token")
        for order in orders or []:
            existing_order = self._get_open_order(order)
            if existing_order and existing_order.state == "draft":
                existing_order._pba_check_sync_lock(device_token)
        return super().sync_from_ui(orders)
