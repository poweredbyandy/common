from uuid import uuid4

from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPosOrderLock(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env["res.partner"].create({"name": "PBA Lock Partner"})
        sale_tax = cls.env["account.tax"].search(
            [
                ("type_tax_use", "=", "sale"),
                ("company_id", "=", cls.company.id),
                ("amount_type", "=", "percent"),
            ],
            limit=1,
        )
        if not sale_tax:
            sale_tax = cls.env["account.tax"].create(
                {
                    "name": "PBA Lock Sale Tax",
                    "amount": 16.0,
                    "amount_type": "percent",
                    "type_tax_use": "sale",
                    "company_id": cls.company.id,
                }
            )
        cls.product = cls.env["product.product"].create(
            {
                "name": "PBA Lock Product",
                "available_in_pos": True,
                "list_price": 10.0,
                "taxes_id": [(6, 0, sale_tax.ids)],
            }
        )
        cash_journal = cls.env["account.journal"].create(
            {
                "name": "PBA Lock Cash",
                "type": "cash",
                "code": "P%s" % uuid4().hex[:4].upper(),
                "company_id": cls.company.id,
            }
        )
        cls.cash_method = cls.env["pos.payment.method"].create(
            {
                "name": "PBA Lock Cash",
                "journal_id": cash_journal.id,
                "company_id": cls.company.id,
            }
        )
        cls.pos_config = cls.env["pos.config"].create(
            {
                "name": "PBA Lock Shop",
                "payment_method_ids": [(6, 0, cls.cash_method.ids)],
            }
        )
        cls.pos_config.open_ui()
        cls.pos_session = cls.pos_config.current_session_id
        cls.pos_session.set_opening_control(0, None)
        cls.PosOrder = cls.env["pos.order"]

    def _create_draft_order(self, uuid_value=None):
        uuid_value = uuid_value or str(uuid4())
        return self.PosOrder.create(
            {
                "company_id": self.company.id,
                "session_id": self.pos_session.id,
                "partner_id": self.partner.id,
                "amount_tax": 0.0,
                "amount_total": 10.0,
                "amount_paid": 0.0,
                "amount_return": 0.0,
                "uuid": uuid_value,
                "pos_reference": "Order %s" % uuid_value,
                "lines": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "price_unit": 10.0,
                            "qty": 1,
                            "price_subtotal": 10.0,
                            "price_subtotal_incl": 10.0,
                            "tax_ids": [(6, 0, [])],
                        },
                    )
                ],
            }
        )

    def test_remote_product_price_uses_pos_currency_conversion(self):
        product_model = self.env["product.product"]
        expected = product_model._load_product_with_domain(
            [("id", "=", self.product.id)],
            self.pos_config.id,
        )
        product_model._process_pos_ui_product_product(expected, self.pos_config)
        prices = product_model.pba_get_pos_currency_prices(
            [self.product.id],
            self.pos_config.id,
        )
        self.assertEqual(
            prices[self.product.id]["lst_price"],
            expected[0]["lst_price"],
        )

    def _order_sync_payload(self, order):
        line = order.lines[0]
        order._ensure_access_token()
        return {
            "id": order.id,
            "uuid": order.uuid,
            "access_token": order.access_token,
            "name": order.pos_reference,
            "session_id": order.session_id.id,
            "partner_id": order.partner_id.id,
            "user_id": self.env.uid,
            "amount_tax": order.amount_tax,
            "amount_total": order.amount_total,
            "amount_paid": 0.0,
            "amount_return": 0.0,
            "sequence_number": order.sequence_number or 1,
            "date_order": fields.Datetime.to_string(fields.Datetime.now()),
            "fiscal_position_id": False,
            "pricelist_id": self.pos_config.pricelist_id.id,
            "to_invoice": False,
            "state": "draft",
            "last_order_preparation_change": "{}",
            "lines": [
                (
                    1,
                    line.id,
                    {
                        "product_id": line.product_id.id,
                        "qty": line.qty,
                        "price_unit": line.price_unit,
                        "price_subtotal": line.price_subtotal,
                        "price_subtotal_incl": line.price_subtotal_incl,
                        "discount": 0.0,
                        "tax_ids": [(6, 0, line.tax_ids.ids)],
                        "pack_lot_ids": [],
                        "uuid": line.uuid or str(uuid4()),
                    },
                )
            ],
            "payment_ids": [],
            "pba_lock_device_token": "should-be-stripped",
            "pba_lock_owner_name": "should-be-stripped",
            "pba_lock_expire": fields.Datetime.to_string(fields.Datetime.now()),
        }

    def test_acquire_renew_release_lock(self):
        order = self._create_draft_order()
        result = self.PosOrder.pba_acquire_order_lock(
            order.id, "device-a", "Cashier A", self.env.user.id, False
        )
        self.assertTrue(result["success"])
        self.assertEqual(order.pba_lock_device_token, "device-a")
        self.assertEqual(order.pba_lock_owner_name, "Cashier A")
        self.assertEqual(order.pba_lock_owner_user_id, self.env.user.id)
        self.assertFalse(order.pba_lock_owner_employee_id)
        self.assertTrue(order.pba_lock_expire)

        renew = self.PosOrder.pba_renew_order_lock(order.id, "device-a")
        self.assertTrue(renew["success"])
        self.assertEqual(order.pba_lock_device_token, "device-a")

        release = self.PosOrder.pba_release_order_lock(order.id, "device-a")
        self.assertTrue(release["success"])
        self.assertFalse(order.pba_lock_device_token)
        self.assertFalse(order.pba_lock_owner_name)
        self.assertFalse(order.pba_lock_owner_user_id)
        self.assertFalse(order.pba_lock_owner_employee_id)
        self.assertFalse(order.pba_lock_expire)

    def test_acquire_rejects_other_device(self):
        order = self._create_draft_order()
        self.PosOrder.pba_acquire_order_lock(order.id, "device-a", "Cashier A")
        busy = self.PosOrder.pba_acquire_order_lock(order.id, "device-b", "Cashier B")
        self.assertFalse(busy["success"])
        self.assertEqual(busy["owner_name"], "Cashier A")
        self.assertEqual(order.pba_lock_device_token, "device-a")

    def test_get_order_locks_returns_current_owner(self):
        order = self._create_draft_order()
        self.PosOrder.pba_acquire_order_lock(
            order.id, "device-a", "Cashier A", self.env.user.id, False
        )
        result = self.PosOrder.pba_get_order_locks([order.id])
        self.assertTrue(result["success"])
        self.assertEqual(len(result["order"]), 1)
        self.assertEqual(result["order"][0]["pba_lock_device_token"], "device-a")
        self.assertEqual(result["order"][0]["pba_lock_owner_name"], "Cashier A")
        self.assertEqual(result["order"][0]["pba_lock_owner_user_id"], self.env.user.id)
        self.assertEqual(result["order"][0]["state"], "draft")

    def test_acquire_rejects_processed_order(self):
        order = self._create_draft_order()
        order.write({"state": "paid"})
        result = self.PosOrder.pba_acquire_order_lock(order.id, "device-a", "Cashier A")
        self.assertFalse(result["success"])
        self.assertEqual(result["reason"], "processed")
        self.assertEqual(result["order"][0]["state"], "paid")
        self.assertFalse(order.pba_lock_device_token)

    def test_lock_expires_and_can_be_reacquired(self):
        order = self._create_draft_order()
        with freeze_time("2026-08-07 10:00:00"):
            self.PosOrder.pba_acquire_order_lock(order.id, "device-a", "Cashier A")
            expire = order.pba_lock_expire
            self.assertEqual(expire, fields.Datetime.from_string("2026-08-07 10:00:30"))

        with freeze_time("2026-08-07 10:00:31"):
            result = self.PosOrder.pba_acquire_order_lock(order.id, "device-b", "Cashier B")
            self.assertTrue(result["success"])
            self.assertEqual(order.pba_lock_device_token, "device-b")
            self.assertEqual(order.pba_lock_owner_name, "Cashier B")

    def test_renew_rejects_other_device(self):
        order = self._create_draft_order()
        self.PosOrder.pba_acquire_order_lock(order.id, "device-a", "Cashier A")
        renew = self.PosOrder.pba_renew_order_lock(order.id, "device-b")
        self.assertFalse(renew["success"])

    def test_renew_does_not_bump_write_date(self):
        order = self._create_draft_order()
        with freeze_time("2099-08-07 10:00:00"):
            self.PosOrder.pba_acquire_order_lock(order.id, "device-a", "Cashier A")
            write_date_before = order.write_date
            partner_before = order.partner_id
        with freeze_time("2099-08-07 10:00:10"):
            renew = self.PosOrder.pba_renew_order_lock(order.id, "device-a")
        self.assertTrue(renew["success"])
        order.invalidate_recordset(["pba_lock_expire"], flush=False)
        self.assertEqual(order.write_date, write_date_before)
        self.assertEqual(order.partner_id, partner_before)
        self.assertEqual(
            order.pba_lock_expire,
            fields.Datetime.from_string("2099-08-07 10:00:40"),
        )

    def test_renew_does_not_notify_other_devices(self):
        order = self._create_draft_order()
        self.PosOrder.pba_acquire_order_lock(order.id, "device-a", "Cashier A")
        notify_calls = []

        def _track_notify(self_order):
            notify_calls.append(self_order.id)

        self.patch(
            type(order),
            "_pba_notify_lock_change",
            _track_notify,
        )
        renew = self.PosOrder.pba_renew_order_lock(order.id, "device-a")
        self.assertTrue(renew["success"])
        self.assertFalse(notify_calls)

    def test_sync_from_ui_rejects_other_device(self):
        order = self._create_draft_order()
        self.PosOrder.pba_acquire_order_lock(order.id, "device-a", "Cashier A")
        payload = self._order_sync_payload(order)
        with self.assertRaises(UserError):
            self.PosOrder.with_context(pba_device_token="device-b").sync_from_ui([payload])

    def test_sync_from_ui_allows_owner_and_strips_lock_fields(self):
        order = self._create_draft_order()
        self.PosOrder.pba_acquire_order_lock(order.id, "device-a", "Cashier A")
        expire_before = order.pba_lock_expire
        payload = self._order_sync_payload(order)
        self.PosOrder.with_context(pba_device_token="device-a").sync_from_ui([payload])
        order.invalidate_recordset()
        self.assertEqual(order.pba_lock_device_token, "device-a")
        self.assertEqual(order.pba_lock_owner_name, "Cashier A")
        self.assertEqual(order.pba_lock_expire, expire_before)

    def test_sync_from_ui_allows_after_expiration(self):
        order = self._create_draft_order()
        with freeze_time("2026-08-07 10:00:00"):
            self.PosOrder.pba_acquire_order_lock(order.id, "device-a", "Cashier A")
        payload = self._order_sync_payload(order)
        with freeze_time("2026-08-07 10:00:31"):
            self.PosOrder.with_context(pba_device_token="device-b").sync_from_ui([payload])
        order.invalidate_recordset()
        self.assertTrue(order.exists())
