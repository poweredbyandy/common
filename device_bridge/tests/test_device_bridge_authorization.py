from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeviceBridgeAuthorization(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.device = cls.env["device.bridge"].create(
            {
                "name": "Test printer",
                "code": "test_printer_nul",
            }
        )
        cls.Auth = cls.env["device.bridge.authorization"]

    def test_authorize_device_strips_nul_from_usb_strings(self):
        payload = self.Auth.authorize_device(
            {
                "device_code": self.device.code,
                "browser_key": "browser-key-1",
                "vendor_id": 0x0416,
                "product_id": 0x5011,
                "serial_number": "ABC\x00DEF",
                "product_name": "Printer\x00",
                "manufacturer_name": "Maker\x00Name",
            }
        )
        self.assertEqual(payload["serial_number"], "ABCDEF")
        self.assertEqual(payload["product_name"], "Printer")
        self.assertEqual(payload["manufacturer_name"], "MakerName")
        auth = self.Auth.browse(payload["id"])
        self.assertEqual(auth.serial_number, "ABCDEF")
        self.assertEqual(auth.product_name, "Printer")
        self.assertEqual(auth.manufacturer_name, "MakerName")

    def test_authorize_device_idempotent_after_nul_strip(self):
        vals = {
            "device_code": self.device.code,
            "browser_key": "browser-key-2",
            "vendor_id": 1046,
            "product_id": 20481,
            "serial_number": "SN001\x00",
            "product_name": "POS-80",
        }
        first = self.Auth.authorize_device(vals)
        second = self.Auth.authorize_device(
            dict(vals, serial_number="SN001", product_name="POS-80")
        )
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(
            self.Auth.search_count([("browser_key", "=", "browser-key-2")]),
            1,
        )

    def test_get_shareable_device_codes(self):
        self.Auth.authorize_device(
            {
                "device_code": self.device.code,
                "browser_key": "browser-key-share",
                "vendor_id": 1046,
                "product_id": 20481,
            }
        )
        codes = self.env["device.bridge"].get_shareable_device_codes()
        self.assertIn(self.device.code, codes)
