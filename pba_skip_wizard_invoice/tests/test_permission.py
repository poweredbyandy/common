from odoo.exceptions import UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestPbaSkipWizardInvoicePermission(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "PBA Skip Wizard Partner"}
        )
        cls.order = cls.env["sale.order"].create({"partner_id": cls.partner.id})

    def test_user_without_group_cannot_confirm_and_invoice(self):
        user = new_test_user(
            self.env,
            login="pba_skip_invoice_no_perm",
            groups="base.group_user,sales_team.group_sale_salesman",
        )
        with self.assertRaises(UserError):
            self.order.with_user(user).action_confirm_create_and_post_invoice()

    def test_user_with_group_passes_permission_check(self):
        user = new_test_user(
            self.env,
            login="pba_skip_invoice_with_perm",
            groups=(
                "base.group_user,"
                "sales_team.group_sale_salesman,"
                "pba_skip_wizard_invoice.group_sale_confirm_create_invoice"
            ),
        )
        order = self.order.with_user(user)
        with self.assertRaises(UserError) as error:
            order.action_confirm_create_and_post_invoice()
        self.assertNotIn("permiso", error.exception.args[0].lower())
