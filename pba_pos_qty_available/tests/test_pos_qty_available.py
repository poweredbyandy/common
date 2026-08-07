from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPbaPosQtyAvailable(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.groups_id |= cls.env.ref("point_of_sale.group_pos_manager")
        cls.company = cls.env.company
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )
        cls.config = cls.env["pos.config"].create(
            {
                "name": "PBA Qty POS",
                "show_product_qty_available": True,
                "warehouse_id": cls.warehouse.id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "PBA Qty Product",
                "is_storable": True,
                "available_in_pos": True,
                "list_price": 10.0,
                "taxes_id": False,
            }
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.product, cls.warehouse.lot_stock_id, 100
        )

    def test_get_pos_free_qty_returns_warehouse_qty(self):
        qty_map = self.env["product.product"].get_pos_free_qty(
            [self.product.id], self.config.id
        )
        self.assertAlmostEqual(qty_map.get(self.product.id), 100.0)

    def test_compute_sellable_qty_without_pending_sales(self):
        qty_map = self.env["pos.config"]._pba_pos_compute_sellable_qty(
            [self.product.id], self.warehouse
        )
        self.assertAlmostEqual(qty_map.get(self.product.id), 100.0)

    def test_load_pos_data_fields_includes_free_qty_when_enabled(self):
        fields = self.env["product.product"]._load_pos_data_fields(self.config.id)
        self.assertIn("free_qty", fields)
        self.config.show_product_qty_available = False
        fields_disabled = self.env["product.product"]._load_pos_data_fields(
            self.config.id
        )
        self.assertNotIn("free_qty", fields_disabled)

    def test_get_pos_free_qty_disabled_config_returns_empty(self):
        self.config.show_product_qty_available = False
        qty_map = self.env["product.product"].get_pos_free_qty(
            [self.product.id], self.config.id
        )
        self.assertEqual(qty_map, {})

    def test_schedule_notify_batches_products(self):
        session = self.env["pos.session"].create(
            {
                "name": "PBA Qty Session",
                "config_id": self.config.id,
                "user_id": self.env.uid,
            }
        )
        self.assertNotEqual(session.state, "closed")
        self.assertTrue(self.env["pos.config"]._pba_pos_has_listening_sessions())
        self.env["pos.config"]._pba_pos_schedule_free_qty_notify([self.product.id])
        pending = self.env.cr.precommit.data.get("pba_pos_free_qty_products")
        self.assertTrue(pending)
        self.assertIn(self.product.id, pending)

    def test_sellable_qty_subtracts_paid_orders_when_stock_at_closing(self):
        session = self.env["pos.session"].create(
            {
                "name": "PBA Closing Session",
                "config_id": self.config.id,
                "user_id": self.env.uid,
            }
        )
        session.write({"update_stock_at_closing": True})
        self.assertTrue(session.update_stock_at_closing)
        order = self.env["pos.order"].create(
            {
                "session_id": session.id,
                "company_id": self.company.id,
                "amount_tax": 0.0,
                "amount_total": 20.0,
                "amount_paid": 20.0,
                "amount_return": 0.0,
                "state": "paid",
            }
        )
        self.env["pos.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "price_unit": 10.0,
                "qty": 2.0,
                "price_subtotal": 20.0,
                "price_subtotal_incl": 20.0,
            }
        )
        self.assertEqual(len(order.lines), 1)
        qty_map = self.env["pos.config"]._pba_pos_compute_sellable_qty(
            [self.product.id], self.warehouse
        )
        self.assertAlmostEqual(qty_map.get(self.product.id), 98.0)
