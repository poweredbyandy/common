from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestPbaSaleConfirmPermission(TransactionCase):

    def test_salesman_from_hook_keeps_confirm_group(self):
        group = self.env.ref("pba_sale_confirm_permission.group_sale_order_confirm")
        salesman = self.env.ref("sales_team.group_sale_salesman")
        existing = salesman.users.filtered(lambda u: not u.share)
        if existing:
            self.assertTrue(any(user in group.users for user in existing))

    def test_new_salesman_without_group_does_not_have_it(self):
        user = new_test_user(
            self.env,
            login="pba_confirm_perm_salesman",
            groups="base.group_user,sales_team.group_sale_salesman",
        )
        self.assertFalse(
            user.has_group("pba_sale_confirm_permission.group_sale_order_confirm")
        )

    def test_group_can_be_granted(self):
        user = new_test_user(
            self.env,
            login="pba_confirm_perm_granted",
            groups=(
                "base.group_user,"
                "sales_team.group_sale_salesman,"
                "pba_sale_confirm_permission.group_sale_order_confirm"
            ),
        )
        self.assertTrue(
            user.has_group("pba_sale_confirm_permission.group_sale_order_confirm")
        )
