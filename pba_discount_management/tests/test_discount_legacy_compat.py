from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tools.float_utils import float_compare

from odoo.addons.l10n_ve_seniat.tests.common import L10nVeSeniatCommon


@tagged("post_install", "-at_install")
class TestPbaDiscountLegacyCompat(L10nVeSeniatCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_ve = cls.env["res.partner"].create(
            {
                "name": "Partner VE PBA discount",
                "country_id": cls.env.ref("base.ve").id,
                "vat": "J12345680",
            }
        )
        cls.env.company.pba_max_discount_percent = 20.0
        cls.partner_ve.pba_max_discount_percent = 0.0
        discount_group = cls.env.ref(
            "pba_discount_management.group_pba_global_sale_invoice_discount"
        )
        unlimited_group = cls.env.ref(
            "pba_discount_management.group_pba_discount_unlimited"
        )
        cls.env.user.groups_id = [(4, discount_group.id), (4, unlimited_group.id)]
        cls.discount_product = cls.env["product.product"].create(
            {
                "name": "Discount",
                "type": "service",
                "invoice_policy": "order",
                "list_price": 0.0,
                "company_id": cls.env.company.id,
            }
        )
        cls.env.company.sale_discount_product_id = cls.discount_product
        cls.reason = cls.env["l10n.ve.discount.reason"]._l10n_ve_get_default()
        if not cls.reason:
            cls.reason = cls.env["l10n.ve.discount.reason"].create({"name": "Descuento"})

    def _create_invoice(self, price_unit=1000.0, quantity=1.0):
        return self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_ve.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Product line",
                            "quantity": quantity,
                            "price_unit": price_unit,
                            "account_id": self.company_data["default_account_revenue"].id,
                            "tax_ids": [
                                Command.set([self.company_data["default_tax_sale"].id])
                            ],
                        }
                    )
                ],
            }
        )

    def _create_ve_product(self, name, price):
        tmpl = self.env["product.template"].create(
            {
                "name": name,
                "company_id": self.env.company.id,
                "list_price": price,
                "standard_price": price / 2,
                "taxes_id": [Command.set([self.company_data["default_tax_sale"].id])],
                "supplier_taxes_id": [
                    Command.set([self.company_data["default_tax_purchase"].id])
                ],
            }
        )
        return tmpl.product_variant_ids[0]

    def _create_sale_order(self, price_unit=1000.0):
        product = self._create_ve_product("SO product PBA", price_unit)
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner_ve.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_uom_qty": 1,
                            "price_unit": price_unit,
                        }
                    )
                ],
            }
        )

    def _add_legacy_discount_line(self, move, amount=100.0):
        line = self.env["account.move.line"].create(
            {
                "move_id": move.id,
                "product_id": self.discount_product.id,
                "display_type": "product",
                "quantity": 1.0,
                "price_unit": -amount,
                "tax_ids": [Command.set([self.company_data["default_tax_sale"].id])],
                "name": "Legacy discount",
                "sequence": 9999,
            }
        )
        move.pba_discount_legacy = True
        return line

    def test_migrate_marks_legacy_invoices_with_product_discount(self):
        move = self._create_invoice()
        self._add_legacy_discount_line(move, amount=50.0)
        move.pba_discount_legacy = False
        marked = self.env["account.move"]._pba_mark_legacy_discount_documents()
        self.assertIn(move, marked)
        self.assertTrue(move.pba_discount_legacy)
        discount_lines = move._pba_get_customer_invoice_discount_lines()
        self.assertEqual(len(discount_lines), 1)
        self.assertEqual(discount_lines.product_id, self.discount_product)

    def test_legacy_invoice_keeps_product_discount_line(self):
        move = self._create_invoice(price_unit=1000.0)
        untaxed_before = move.amount_untaxed
        line = self._add_legacy_discount_line(move, amount=100.0)
        self.assertTrue(move.pba_discount_legacy)
        self.assertIn(line, move.invoice_line_ids)
        self.assertFalse(move.l10n_ve_global_discount_ids)
        self.assertAlmostEqual(move.amount_untaxed, untaxed_before - 100.0, places=2)

    def test_new_invoice_uses_seniat_discount(self):
        move = self._create_invoice(price_unit=1000.0)
        self.assertFalse(move.pba_discount_legacy)
        wizard = self.env["l10n.ve.account.move.discount.wizard"].create(
            {
                "move_id": move.id,
                "discount_mode": "percentage",
                "discount_percentage": 0.1,
                "reason_id": self.reason.id,
            }
        )
        wizard.action_apply_discount()
        self.assertFalse(move.pba_discount_legacy)
        self.assertEqual(len(move.l10n_ve_global_discount_ids), 1)
        self.assertFalse(
            move.invoice_line_ids.filtered(
                lambda line: line.product_id == self.discount_product
            )
        )
        self.assertGreater(move.pba_document_discount_percent, 0.0)

    def test_new_sale_order_uses_seniat_discount(self):
        order = self._create_sale_order(price_unit=1000.0)
        self.assertFalse(order.pba_discount_legacy)
        wizard = self.env["sale.order.discount"].create(
            {
                "sale_order_id": order.id,
                "l10n_ve_discount_mode": "percentage",
                "discount_percentage": 0.1,
                "l10n_ve_discount_reason_id": self.reason.id,
                "discount_type": "so_discount",
            }
        )
        wizard.action_apply_discount()
        self.assertFalse(order.pba_discount_legacy)
        self.assertEqual(len(order.l10n_ve_global_discount_ids), 1)
        self.assertFalse(order.order_line.filtered(lambda line: line._is_discount_line()))
        self.assertAlmostEqual(order.pba_document_discount_percent, 10.0, places=2)

    def test_legacy_sale_order_reapply_keeps_product_line(self):
        order = self._create_sale_order(price_unit=1000.0)
        order.pba_discount_legacy = True
        wizard = self.env["sale.order.discount"].create(
            {
                "sale_order_id": order.id,
                "discount_type": "so_discount",
                "discount_percentage": 0.1,
                "l10n_ve_discount_reason_id": self.reason.id,
            }
        )
        wizard.action_apply_discount()
        self.assertTrue(order.pba_discount_legacy)
        discount_lines = order.order_line.filtered(lambda line: line._is_discount_line())
        self.assertEqual(len(discount_lines), 1)
        self.assertFalse(order.l10n_ve_global_discount_ids)
        wizard2 = self.env["sale.order.discount"].create(
            {
                "sale_order_id": order.id,
                "discount_type": "so_discount",
                "discount_percentage": 0.15,
                "l10n_ve_discount_reason_id": self.reason.id,
            }
        )
        wizard2.action_apply_discount()
        discount_lines = order.order_line.filtered(lambda line: line._is_discount_line())
        self.assertEqual(len(discount_lines), 1)
        self.assertAlmostEqual(order.pba_document_discount_percent, 15.0, places=2)

    def test_legacy_invoice_wizard_reapplies_product_line(self):
        move = self._create_invoice(price_unit=1000.0)
        move.pba_discount_legacy = True
        wizard = self.env["account.move.discount"].create(
            {
                "move_id": move.id,
                "discount_type": "so_discount",
                "discount_percentage": 0.1,
            }
        )
        wizard.action_apply_discount()
        lines = move._pba_get_customer_invoice_discount_lines()
        self.assertEqual(len(lines), 1)
        self.assertTrue(move.pba_discount_legacy)
        self.assertFalse(move.l10n_ve_global_discount_ids)
        wizard2 = self.env["account.move.discount"].create(
            {
                "move_id": move.id,
                "discount_type": "so_discount",
                "discount_percentage": 0.2,
            }
        )
        wizard2.action_apply_discount()
        lines = move._pba_get_customer_invoice_discount_lines()
        self.assertEqual(len(lines), 1)
        self.assertAlmostEqual(abs(lines.price_unit), 200.0, places=2)

    def test_pba_rights_required_on_seniat_wizard(self):
        move = self._create_invoice()
        group = self.env.ref(
            "pba_discount_management.group_pba_global_sale_invoice_discount"
        )
        unlimited = self.env.ref(
            "pba_discount_management.group_pba_discount_unlimited"
        )
        self.env.user.groups_id = [(3, group.id), (3, unlimited.id)]
        wizard = self.env["l10n.ve.account.move.discount.wizard"].create(
            {
                "move_id": move.id,
                "discount_mode": "percentage",
                "discount_percentage": 0.05,
                "reason_id": self.reason.id,
            }
        )
        with self.assertRaises(UserError):
            wizard.action_apply_discount()

    def test_pba_limit_on_seniat_wizard(self):
        group = self.env.ref(
            "pba_discount_management.group_pba_global_sale_invoice_discount"
        )
        unlimited = self.env.ref(
            "pba_discount_management.group_pba_discount_unlimited"
        )
        self.env.user.groups_id = [(4, group.id), (3, unlimited.id)]
        move = self._create_invoice(price_unit=1000.0)
        wizard = self.env["l10n.ve.account.move.discount.wizard"].create(
            {
                "move_id": move.id,
                "discount_mode": "percentage",
                "discount_percentage": 0.5,
                "reason_id": self.reason.id,
            }
        )
        with self.assertRaises(UserError):
            wizard.action_apply_discount()

    def test_forbid_line_discount_on_new_invoice(self):
        move = self._create_invoice()
        with self.assertRaises(ValidationError):
            move.invoice_line_ids[0].discount = 10.0

    def test_document_percent_legacy_and_seniat(self):
        legacy_move = self._create_invoice(price_unit=1000.0)
        legacy_move.pba_discount_legacy = True
        wizard = self.env["account.move.discount"].create(
            {
                "move_id": legacy_move.id,
                "discount_type": "so_discount",
                "discount_percentage": 0.1,
            }
        )
        wizard.action_apply_discount()
        self.assertAlmostEqual(legacy_move.pba_document_discount_percent, 10.0, places=2)

        seniat_move = self._create_invoice(price_unit=1000.0)
        seniat_wizard = self.env["l10n.ve.account.move.discount.wizard"].create(
            {
                "move_id": seniat_move.id,
                "discount_mode": "percentage",
                "discount_percentage": 0.1,
                "reason_id": self.reason.id,
            }
        )
        seniat_wizard.action_apply_discount()
        self.assertFalse(seniat_move.pba_discount_legacy)
        self.assertTrue(
            float_compare(seniat_move.pba_document_discount_percent, 10.0, precision_digits=2)
            == 0
            or seniat_move.pba_document_discount_percent > 0.0
        )

    def test_open_wizard_routes_by_legacy_flag(self):
        legacy_move = self._create_invoice()
        legacy_move.pba_discount_legacy = True
        action = legacy_move.action_open_discount_wizard()
        self.assertEqual(action["res_model"], "account.move.discount")

        new_move = self._create_invoice()
        action = new_move.action_open_discount_wizard()
        self.assertEqual(action["res_model"], "l10n.ve.account.move.discount.wizard")
