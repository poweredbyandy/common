from odoo.addons.stock.tests.common import TestStockCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestProductLabelLayoutStock(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.label_product = cls.env["product.product"].create(
            {
                "name": "QR Label Stock Product",
                "is_storable": True,
                "default_code": "QR-STOCK-9",
                "barcode": "8412345678111",
            }
        )

    def _create_incoming_move(self, quantity):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_in,
                "location_id": self.supplier_location,
                "location_dest_id": self.stock_location,
            }
        )
        move = self.env["stock.move"].create(
            {
                "name": self.label_product.name,
                "product_id": self.label_product.id,
                "product_uom_qty": quantity,
                "product_uom": self.label_product.uom_id.id,
                "picking_id": picking.id,
                "location_id": self.supplier_location,
                "location_dest_id": self.stock_location,
            }
        )
        return move

    def test_qr_label_uses_operation_quantity_from_stock_move(self):
        move = self._create_incoming_move(9)
        wizard = self.env["product.label.layout"].create(
            {
                "print_format": "qr_label_code",
                "move_quantity": "move",
                "move_ids": [(6, 0, move.ids)],
                "product_ids": [(6, 0, self.label_product.ids)],
                "custom_quantity": 1,
            }
        )
        xml_id, data = wizard._prepare_report_data()
        self.assertEqual(xml_id, "product_qrcode.action_report_product_qr_zpl")
        self.assertEqual(data["quantity_by_product"][str(self.label_product.id)], 9)
        zpl_body = self.env[
            "report.product_qrcode.report_product_qr_zpl_document"
        ]._build_zpl_body(data)
        self.assertEqual(zpl_body.count("^XZ"), 9)

    def test_qr_label_prints_one_label_per_lot(self):
        lot_product = self.env["product.product"].create(
            {
                "name": "QR Label Serial Product",
                "is_storable": True,
                "tracking": "serial",
                "default_code": "QR-SERIAL-1",
                "barcode": "8412345678999",
            }
        )
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_in,
                "location_id": self.supplier_location,
                "location_dest_id": self.stock_location,
            }
        )
        move = self.env["stock.move"].create(
            {
                "name": lot_product.name,
                "product_id": lot_product.id,
                "product_uom_qty": 3,
                "product_uom": lot_product.uom_id.id,
                "picking_id": picking.id,
                "location_id": self.supplier_location,
                "location_dest_id": self.stock_location,
            }
        )
        for lot_name in ("SN001", "SN002", "SN003"):
            self.env["stock.move.line"].create(
                {
                    "move_id": move.id,
                    "product_id": lot_product.id,
                    "product_uom_id": lot_product.uom_id.id,
                    "quantity": 1,
                    "lot_name": lot_name,
                    "location_id": self.supplier_location,
                    "location_dest_id": self.stock_location,
                }
            )
        wizard = self.env["product.label.layout"].create(
            {
                "print_format": "qr_label_code",
                "move_quantity": "move",
                "move_ids": [(6, 0, move.ids)],
                "product_ids": [(6, 0, lot_product.ids)],
                "custom_quantity": 1,
            }
        )
        _xml_id, data = wizard._prepare_report_data()
        self.assertIn("custom_barcodes", data)
        zpl_body = self.env[
            "report.product_qrcode.report_product_qr_zpl_document"
        ]._build_zpl_body(data)
        self.assertEqual(zpl_body.count("^XZ"), 3)
        self.assertIn("SN001", zpl_body)
        self.assertIn("SN002", zpl_body)
        self.assertIn("SN003", zpl_body)

    def test_qr_label_custom_quantity_when_not_move_mode(self):
        move = self._create_incoming_move(9)
        wizard = self.env["product.label.layout"].create(
            {
                "print_format": "qr_label_code",
                "move_quantity": "custom",
                "move_ids": [(6, 0, move.ids)],
                "product_ids": [(6, 0, self.label_product.ids)],
                "custom_quantity": 3,
            }
        )
        _xml_id, data = wizard._prepare_report_data()
        self.assertEqual(data["quantity_by_product"][str(self.label_product.id)], 3)
