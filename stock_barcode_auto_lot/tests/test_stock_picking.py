from odoo.addons.stock.tests.common import TestStockCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestStockBarcodeAutoLot(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.serial_product = cls.env["product.product"].create(
            {
                "name": "Auto Lot Serial Product",
                "is_storable": True,
                "tracking": "serial",
                "default_code": "AUTO-SN",
            }
        )
        cls.picking = cls.env["stock.picking"].create(
            {
                "picking_type_id": cls.picking_type_in,
                "location_id": cls.supplier_location,
                "location_dest_id": cls.stock_location,
            }
        )

    def test_get_barcode_next_lot_name_is_unique_in_picking(self):
        lot_name_1 = self.picking.get_barcode_next_lot_name(self.serial_product.id)
        self.env["stock.move.line"].create(
            {
                "picking_id": self.picking.id,
                "product_id": self.serial_product.id,
                "product_uom_id": self.serial_product.uom_id.id,
                "quantity": 1,
                "lot_name": lot_name_1,
                "location_id": self.supplier_location,
                "location_dest_id": self.stock_location,
            }
        )
        lot_name_2 = self.picking.get_barcode_next_lot_name(self.serial_product.id)
        self.assertNotEqual(lot_name_1, lot_name_2)

    def test_get_barcode_next_lot_name_uses_existing_serial_sequence(self):
        self.env["stock.lot"].create(
            {
                "name": "AUTO-SN00009",
                "product_id": self.serial_product.id,
                "company_id": self.env.company.id,
            }
        )
        lot_name = self.picking.get_barcode_next_lot_name(self.serial_product.id)
        self.assertEqual(lot_name, "AUTO-SN00010")
