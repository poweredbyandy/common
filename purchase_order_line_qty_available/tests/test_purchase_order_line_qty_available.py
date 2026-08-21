from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPurchaseOrderLineQtyAvailable(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Vendor Qty Available"})
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.uom_dozen = cls.env.ref("uom.product_uom_dozen")
        cls.product = cls.env["product.product"].create(
            {
                "name": "Storable Qty Available",
                "type": "consu",
                "is_storable": True,
                "purchase_ok": True,
                "uom_id": cls.uom_unit.id,
                "uom_po_id": cls.uom_unit.id,
            }
        )
        cls.service = cls.env["product.product"].create(
            {
                "name": "Service Qty Available",
                "type": "service",
                "purchase_ok": True,
                "uom_id": cls.uom_unit.id,
                "uom_po_id": cls.uom_unit.id,
            }
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.product, cls.warehouse.lot_stock_id, 12.0
        )

    def _create_order(self, product, product_uom=None, picking_type=None, qty=1.0):
        return self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": (picking_type or self.warehouse.in_type_id).id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_qty": qty,
                            "product_uom": (product_uom or product.uom_po_id).id,
                            "price_unit": 1.0,
                        },
                    )
                ],
            }
        )

    def test_storable_shows_on_hand_qty(self):
        order = self._create_order(self.product)
        self.assertEqual(order.order_line.qty_available, 12.0)

    def test_service_has_zero_qty(self):
        order = self._create_order(self.service)
        self.assertEqual(order.order_line.qty_available, 0.0)

    def test_qty_converted_to_line_uom(self):
        order = self._create_order(self.product, product_uom=self.uom_dozen)
        self.assertEqual(order.order_line.qty_available, 1.0)

    def test_qty_uses_destination_warehouse(self):
        warehouse_b = self.env["stock.warehouse"].create(
            {
                "name": "Warehouse B Qty",
                "code": "WQB",
                "company_id": self.env.company.id,
            }
        )
        order_a = self._create_order(self.product)
        order_b = self._create_order(
            self.product, picking_type=warehouse_b.in_type_id
        )
        self.assertEqual(order_a.order_line.qty_available, 12.0)
        self.assertEqual(order_b.order_line.qty_available, 0.0)
