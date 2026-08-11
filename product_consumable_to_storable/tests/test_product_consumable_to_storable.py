from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestProductConsumableToStorable(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.supplier_location = cls.env.ref("stock.stock_location_suppliers")
        cls.stock_location = cls.env.ref("stock.stock_location_stock")
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.product = cls.env["product.product"].create(
            {
                "name": "Consumable to convert",
                "type": "consu",
                "is_storable": False,
                "tracking": "none",
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

    def test_convert_rebuilds_quantity_from_moves(self):
        self._create_done_move(
            self.product, self.supplier_location, self.stock_location, 10
        )
        self._create_done_move(
            self.product, self.stock_location, self.customer_location, 3
        )
        self.assertFalse(self.product.is_storable)
        self.assertEqual(self.product.qty_available, 0.0)

        with self.assertRaises(UserError):
            self.product.product_tmpl_id.write({"is_storable": True})

        wizard = (
            self.env["product.consumable.to.storable.wizard"]
            .with_context(
                active_model="product.template",
                active_ids=self.product.product_tmpl_id.ids,
            )
            .create({})
        )
        wizard.action_convert()

        self.assertTrue(self.product.is_storable)
        self.assertEqual(self.product.tracking, "none")
        self.assertEqual(self.product.qty_available, 7.0)

    def test_reject_already_storable_or_service(self):
        storable = self.env["product.product"].create(
            {
                "name": "Already storable",
                "type": "consu",
                "is_storable": True,
            }
        )
        service = self.env["product.product"].create(
            {
                "name": "Service product",
                "type": "service",
            }
        )
        wizard = (
            self.env["product.consumable.to.storable.wizard"]
            .with_context(
                active_model="product.product",
                active_ids=(storable | service).ids,
            )
            .create({})
        )
        with self.assertRaises(UserError):
            wizard.action_convert()
