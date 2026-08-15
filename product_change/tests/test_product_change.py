from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestProductChange(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.groups_id += cls.env.ref("stock.group_stock_manager")
        warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.supplier_location = cls.env.ref("stock.stock_location_suppliers")
        cls.stock_location = warehouse.lot_stock_id
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.Wizard = cls.env["product.change.wizard"]

    def _make_product(self, name, product_type="consu", is_storable=False):
        return self.env["product.product"].create(
            {
                "name": name,
                "type": product_type,
                "is_storable": is_storable,
                "tracking": "none",
                "uom_id": self.uom_unit.id,
                "uom_po_id": self.uom_unit.id,
                "list_price": 10.0,
                "standard_price": 5.0,
                "property_account_income_id": self.company_data[
                    "default_account_revenue"
                ].id,
                "property_account_expense_id": self.company_data[
                    "default_account_expense"
                ].id,
            }
        )

    def _create_done_move(self, product, source, destination, quantity):
        move = self.env["stock.move"].create(
            {
                "name": product.display_name,
                "product_id": product.id,
                "product_uom": product.uom_id.id,
                "product_uom_qty": quantity,
                "location_id": source.id,
                "location_dest_id": destination.id,
            }
        )
        move._action_confirm()
        move.quantity = quantity
        move.picked = True
        move._action_done()
        return move

    def _open_wizard(self, templates, **values):
        wizard = self.Wizard.with_context(
            active_model="product.template",
            active_ids=templates.ids,
        ).create(values)
        return wizard

    def test_reject_empty_selection(self):
        product = self._make_product("Empty change")
        wizard = self._open_wizard(product.product_tmpl_id)
        with self.assertRaises(UserError):
            wizard.action_apply()

    def test_reject_combo(self):
        item = self._make_product("Combo item")
        combo_choice = self.env["product.combo"].create(
            {
                "name": "Choice",
                "combo_item_ids": [(0, 0, {"product_id": item.id})],
            }
        )
        combo = self.env["product.product"].create(
            {
                "name": "Combo product",
                "type": "combo",
                "combo_ids": [(4, combo_choice.id)],
            }
        )
        wizard = self._open_wizard(
            combo.product_tmpl_id,
            change_type=True,
            new_type="consu",
        )
        with self.assertRaises(UserError):
            wizard.action_apply()

    def test_consumable_to_quantity_tracking_rebuilds_stock(self):
        product = self._make_product("Consumable stock")
        self._create_done_move(product, self.supplier_location, self.stock_location, 10)
        self._create_done_move(product, self.stock_location, self.customer_location, 3)
        self.assertFalse(product.is_storable)
        self.assertEqual(product.qty_available, 0.0)

        wizard = self._open_wizard(
            product.product_tmpl_id,
            change_tracking=True,
            new_tracking="quantity",
        )
        wizard.action_apply()

        self.assertTrue(product.is_storable)
        self.assertEqual(product.tracking, "none")
        self.assertEqual(product.qty_available, 7.0)

    def test_quantity_tracking_to_no_tracking(self):
        product = self._make_product("Storable stock", is_storable=True)
        self._create_done_move(product, self.supplier_location, self.stock_location, 4)
        self.assertEqual(product.qty_available, 4.0)

        wizard = self._open_wizard(
            product.product_tmpl_id,
            change_tracking=True,
            new_tracking="none",
        )
        wizard.action_apply()

        self.assertFalse(product.is_storable)
        self.assertEqual(product.qty_available, 0.0)

    def test_service_to_goods_keeps_sale_and_generates_outgoing(self):
        product = self._make_product("Service to goods", product_type="service")
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom_qty": 5,
                            "price_unit": 10,
                        },
                    )
                ],
            }
        )
        sale_order.action_confirm()
        sale_order.order_line.qty_delivered = 5
        invoice = sale_order._create_invoices()
        invoice.action_post()

        wizard = self._open_wizard(
            product.product_tmpl_id,
            change_type=True,
            new_type="consu",
            change_tracking=True,
            new_tracking="quantity",
        )
        wizard.action_apply()

        self.assertEqual(product.type, "consu")
        self.assertTrue(product.is_storable)
        self.assertEqual(sale_order.state, "sale")
        self.assertEqual(invoice.state, "posted")
        self.assertEqual(sale_order.order_line.qty_delivered, 5.0)
        done_moves = sale_order.order_line.move_ids.filtered(
            lambda move: move.state == "done"
        )
        self.assertTrue(done_moves)
        self.assertEqual(sum(done_moves.mapped("quantity")), 5.0)
        self.assertEqual(product.qty_available, -5.0)

    def test_goods_to_service_keeps_sale_and_invoice(self):
        product = self._make_product("Goods to service")
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom_qty": 2,
                            "price_unit": 15,
                        },
                    )
                ],
            }
        )
        sale_order.action_confirm()
        picking = sale_order.picking_ids
        picking.move_ids.quantity = 2
        picking.move_ids.picked = True
        picking.button_validate()
        invoice = sale_order._create_invoices()
        invoice.action_post()

        wizard = self._open_wizard(
            product.product_tmpl_id,
            change_type=True,
            new_type="service",
        )
        wizard.action_apply()

        self.assertEqual(product.type, "service")
        self.assertFalse(product.is_storable)
        self.assertEqual(sale_order.state, "sale")
        self.assertEqual(invoice.state, "posted")
        self.assertEqual(sale_order.order_line.qty_delivered, 2.0)

    def test_service_to_goods_keeps_purchase_and_generates_incoming(self):
        product = self._make_product("Purchased service", product_type="service")
        purchase_order = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_qty": 6,
                            "price_unit": 4,
                        },
                    )
                ],
            }
        )
        purchase_order.button_confirm()
        purchase_order.order_line.qty_received = 6

        wizard = self._open_wizard(
            product.product_tmpl_id,
            change_type=True,
            new_type="consu",
            change_tracking=True,
            new_tracking="quantity",
        )
        wizard.action_apply()

        self.assertEqual(product.type, "consu")
        self.assertTrue(product.is_storable)
        self.assertEqual(purchase_order.state, "purchase")
        self.assertEqual(purchase_order.order_line.qty_received, 6.0)
        done_moves = purchase_order.order_line.move_ids.filtered(
            lambda move: move.state == "done"
        )
        self.assertTrue(done_moves)
        self.assertEqual(product.qty_available, 6.0)

    def test_change_uom_converts_sale_quantities(self):
        product = self._make_product("Uom product")
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom_qty": 24,
                            "price_unit": 1,
                        },
                    )
                ],
            }
        )
        wizard = self._open_wizard(
            product.product_tmpl_id,
            change_uom=True,
            new_uom_id=self.uom_dozen.id,
            convert_uom_qty=True,
        )
        wizard.action_apply()

        self.assertEqual(product.uom_id, self.uom_dozen)
        self.assertEqual(sale_order.order_line.product_uom, self.uom_dozen)
        self.assertEqual(sale_order.order_line.product_uom_qty, 2.0)
        self.assertEqual(sale_order.order_line.price_unit, 12.0)

    def test_direct_invoice_generates_outgoing_stock(self):
        product = self._make_product("Invoiced service", product_type="service")
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "quantity": 3,
                            "price_unit": 20,
                        },
                    )
                ],
            }
        )
        invoice.action_post()

        wizard = self._open_wizard(
            product.product_tmpl_id,
            change_type=True,
            new_type="consu",
            change_tracking=True,
            new_tracking="quantity",
        )
        wizard.action_apply()

        self.assertEqual(product.type, "consu")
        self.assertTrue(product.is_storable)
        self.assertEqual(invoice.state, "posted")
        self.assertEqual(product.qty_available, -3.0)
