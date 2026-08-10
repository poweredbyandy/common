from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged, TransactionCase
from odoo.tests.common import new_test_user


class FakeSession(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as err:
            raise AttributeError(name) from err

    def __setattr__(self, name, value):
        self[name] = value


@tagged("post_install", "-at_install")
class TestResUsersUser(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(
            cls.env,
            login="shared_seller",
            groups="base.group_user,base.group_partner_manager,hr.group_hr_user",
        )
        cls.employee_a = cls.env["hr.employee"].create({
            "name": "Seller A",
            "pin": "1234",
        })
        cls.employee_b = cls.env["hr.employee"].create({
            "name": "Seller B",
            "pin": "5678",
        })
        cls.sub_a = cls.env["res.users.user"].create({
            "user_id": cls.user.id,
            "employee_id": cls.employee_a.id,
        })
        cls.sub_b = cls.env["res.users.user"].create({
            "user_id": cls.user.id,
            "employee_id": cls.employee_b.id,
        })

    def test_pin_validation(self):
        self.sub_a._check_pin("1234")
        with self.assertRaises(UserError):
            self.sub_a._check_pin("0000")

    def test_active_requires_pin(self):
        employee = self.env["hr.employee"].create({"name": "No PIN"})
        with self.assertRaises(ValidationError):
            self.env["res.users.user"].create({
                "user_id": self.user.id,
                "employee_id": employee.id,
            })

    def test_pin_set_from_sub_user(self):
        employee = self.env["hr.employee"].create({"name": "PIN From Sub"})
        sub_user = self.env["res.users.user"].create({
            "user_id": self.user.id,
            "employee_id": employee.id,
            "pin": "9876",
        })
        self.assertEqual(employee.sudo().pin, "9876")
        self.assertEqual(sub_user.pin, "9876")
        sub_user.write({"pin": "1111"})
        self.assertEqual(employee.sudo().pin, "1111")

    def test_audit_log_and_message_sub_user(self):
        partner = (
            self.env["res.partner"]
            .with_user(self.user)
            .with_context(sub_user_id=self.sub_a.id)
            .create({"name": "Tracked Partner"})
        )
        self.assertEqual(partner.create_uid, self.user)
        log = self.env["res.users.user.log"].sudo().search([
            ("model", "=", "res.partner"),
            ("res_id", "=", partner.id),
            ("method", "=", "create"),
            ("sub_user_id", "=", self.sub_a.id),
        ])
        self.assertTrue(log)
        partner.message_post(body="Hello")
        message = self.env["mail.message"].search([
            ("model", "=", "res.partner"),
            ("res_id", "=", partner.id),
            ("body", "ilike", "Hello"),
        ], limit=1)
        self.assertEqual(message.sub_user_id, self.sub_a)

    def test_required_blocks_write_without_sub_user(self):
        self.user.sub_user_required = True
        partner = self.env["res.partner"].create({"name": "Block Me"})
        with self.assertRaises(UserError):
            partner.with_user(self.user).write({"name": "Blocked"})

    def test_login_lock_session(self):
        self.user.sub_user_required = True
        fake_session = FakeSession()
        fake_request = MagicMock()
        fake_request.session = fake_session
        context = {}

        def update_context(**kwargs):
            context.update(kwargs)

        fake_request.update_context.side_effect = update_context

        with patch(
            "odoo.addons.res_users_user.models.res_users.request",
            fake_request,
        ):
            user_env = self.user.with_user(self.user)
            payload = user_env.res_users_user_get_session()
            self.assertTrue(payload["enabled"])
            self.assertTrue(payload["locked"])
            with self.assertRaises(UserError):
                user_env.res_users_user_login(self.sub_a.id, "0000")
            payload = user_env.res_users_user_login(self.sub_a.id, "1234")
            self.assertFalse(payload["locked"])
            self.assertEqual(payload["current_sub_user_id"], self.sub_a.id)
            self.assertEqual(fake_session.get("sub_user_id"), self.sub_a.id)
            self.assertEqual(context.get("sub_user_id"), self.sub_a.id)
            payload = user_env.res_users_user_lock()
            self.assertTrue(payload["locked"])
            self.assertFalse(payload["current_sub_user_id"])
            self.assertFalse(fake_session.get("sub_user_id"))
