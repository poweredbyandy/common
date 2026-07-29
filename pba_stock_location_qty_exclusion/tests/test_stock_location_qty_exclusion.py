from odoo.tests import TransactionCase


class TestStockLocationQuantityExclusion(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env.ref("stock.warehouse0")
        cls.included_location = cls.env["stock.location"].create(
            {
                "name": "Included",
                "location_id": cls.warehouse.lot_stock_id.id,
            }
        )
        cls.excluded_location = cls.env["stock.location"].create(
            {
                "name": "Excluded",
                "location_id": cls.warehouse.lot_stock_id.id,
            }
        )
        cls.excluded_child_location = cls.env["stock.location"].create(
            {
                "name": "Excluded Child",
                "location_id": cls.excluded_location.id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Quantity Exclusion Product",
                "is_storable": True,
            }
        )
        quant_model = cls.env["stock.quant"]
        quant_model._update_available_quantity(
            cls.product,
            cls.included_location,
            5.0,
        )
        quant_model._update_available_quantity(
            cls.product,
            cls.excluded_location,
            4.0,
        )
        quant_model._update_available_quantity(
            cls.product,
            cls.excluded_child_location,
            9.0,
        )
        quant_model._update_reserved_quantity(
            cls.product,
            cls.included_location,
            1.0,
        )
        quant_model._update_reserved_quantity(
            cls.product,
            cls.excluded_location,
            1.0,
        )
        quant_model._update_reserved_quantity(
            cls.product,
            cls.excluded_child_location,
            2.0,
        )

    def test_excludes_location_and_descendants(self):
        self.assertEqual(self.product.qty_available, 18.0)
        self.assertEqual(self.product.free_qty, 14.0)
        self.assertEqual(self.product.product_tmpl_id.qty_available, 18.0)

        self.excluded_location.exclude_from_available_quantity = True

        self.assertEqual(self.product.qty_available, 18.0)
        self.assertEqual(self.product.free_qty, 4.0)
        self.assertEqual(self.product.virtual_available, 18.0)
        self.assertEqual(self.product.product_tmpl_id.qty_available, 18.0)
        product_at_excluded_location = self.product.with_context(
            location=self.excluded_location.id
        )
        self.assertEqual(product_at_excluded_location.qty_available, 13.0)
        self.assertEqual(product_at_excluded_location.free_qty, 0.0)

    def test_excludes_only_selected_subtree(self):
        self.excluded_child_location.exclude_from_available_quantity = True

        self.assertEqual(self.product.qty_available, 18.0)
        self.assertEqual(self.product.free_qty, 7.0)

    def test_quantity_searches_use_separate_values(self):
        self.excluded_location.exclude_from_available_quantity = True

        matching_product = self.env["product.product"].search(
            [
                ("id", "=", self.product.id),
                ("qty_available", "=", 18.0),
            ]
        )
        self.assertEqual(matching_product, self.product)

        matching_product = self.env["product.product"].search(
            [
                ("id", "=", self.product.id),
                ("free_qty", "=", 4.0),
            ]
        )
        self.assertEqual(matching_product, self.product)

    def test_location_domain_keeps_on_hand_quantity(self):
        self.excluded_location.exclude_from_available_quantity = True

        quant_domain = self.product._get_domain_locations_new(
            {self.warehouse.view_location_id.id}
        )[0]
        quants = self.env["stock.quant"].search(
            [("product_id", "=", self.product.id)] + quant_domain
        )

        self.assertEqual(sum(quants.mapped("quantity")), 18.0)

    def test_product_quant_action_shows_excluded_stock(self):
        self.excluded_location.exclude_from_available_quantity = True

        action = self.product.action_open_quants()
        quants = self.env["stock.quant"].with_context(action["context"]).search(
            [
                ("product_id", "=", self.product.id),
                ("on_hand", "=", True),
            ]
        )

        self.assertEqual(self.product.qty_available, 18.0)
        self.assertEqual(sum(quants.mapped("quantity")), 18.0)

    def test_quant_operations_keep_excluded_stock(self):
        available_quantity = self.env["stock.quant"]._get_available_quantity(
            self.product,
            self.excluded_location,
            strict=True,
        )
        self.excluded_location.exclude_from_available_quantity = True

        self.assertEqual(available_quantity, 3.0)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.product,
                self.excluded_location,
                strict=True,
            ),
            3.0,
        )
