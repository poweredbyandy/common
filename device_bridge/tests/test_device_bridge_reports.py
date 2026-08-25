import base64

from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeviceBridgeReports(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.printer = cls.env["device.bridge"].create(
            {
                "name": "Kitchen printer",
                "code": "test_kitchen_printer",
                "device_type": "printer",
            }
        )
        cls.scanner = cls.env["device.bridge"].create(
            {
                "name": "Barcode scanner",
                "code": "test_barcode_scanner",
                "device_type": "scanner",
            }
        )
        cls.report = cls.env["ir.actions.report"].create(
            {
                "name": "Device Bridge Test Report",
                "model": "res.partner",
                "report_type": "qweb-pdf",
                "report_name": "device_bridge.test_partner_report",
            }
        )

    def test_assign_reports_to_printer(self):
        self.printer.write({"report_ids": [(6, 0, self.report.ids)]})
        self.assertEqual(self.printer.report_count, 1)
        self.assertIn(self.printer, self.report.device_bridge_ids)

    def test_assign_printer_from_report(self):
        self.report.write({"device_bridge_ids": [(4, self.printer.id)]})
        self.assertEqual(self.printer.report_ids, self.report)

    def test_reports_only_on_printers(self):
        with self.assertRaises(ValidationError):
            self.scanner.write({"report_ids": [(6, 0, self.report.ids)]})

    def test_get_printers_for_report(self):
        self.printer.write({"report_ids": [(4, self.report.id)]})
        payloads = self.env["device.bridge"].get_printers_for_report(self.report)
        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0]["code"], self.printer.code)
        self.assertEqual(payloads[0]["report_ids"], self.report.ids)
        self.assertIn(self.report.report_name, payloads[0]["report_names"])

    def test_get_device_payload_includes_reports(self):
        self.printer.write({"report_ids": [(4, self.report.id)]})
        payload = self.env["device.bridge"].get_device_payload(self.printer.code)
        self.assertEqual(payload["report_ids"], self.report.ids)
        self.assertEqual(payload["report_names"], [self.report.report_name])

    def test_prepare_print_without_printer_returns_false(self):
        job = self.env["ir.actions.report"].prepare_device_bridge_print(
            self.report.id, [self.env.user.partner_id.id]
        )
        self.assertFalse(job)

    def test_prepare_print_with_printer_returns_job(self):
        self.printer.write({"report_ids": [(4, self.report.id)]})

        def _fake_render(this, report_ref, res_ids, data=None):
            return b"ESC/POS payload", "text"

        self.patch(
            self.env.registry["ir.actions.report"],
            "_render",
            _fake_render,
        )
        job = self.env["ir.actions.report"].prepare_device_bridge_print(
            self.report.id, [self.env.user.partner_id.id]
        )
        self.assertTrue(job)
        self.assertEqual(job["printers"][0]["code"], self.printer.code)
        self.assertEqual(job["report_type"], "qweb-pdf")
        self.assertEqual(base64.b64decode(job["data_b64"]), b"ESC/POS payload")

    def test_zpl_test_print_payload(self):
        printer = self.env["device.bridge"].create(
            {
                "name": "ZPL Test",
                "code": "test_zpl_printer",
                "device_type": "label_printer",
                "protocol": "zpl",
            }
        )
        job = self.env["device.bridge"].get_test_print_payload(printer.code)
        raw = base64.b64decode(job["data_b64"])
        self.assertEqual(job["protocol"], "zpl")
        self.assertIn(b"^XA", raw)
        self.assertIn(b"^XZ", raw)
        self.assertIn(b"ZPL", raw)
        action = printer.action_print_test()
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "device_bridge_print_test")
        self.assertEqual(action["params"]["device_code"], printer.code)

    def test_test_print_rejects_non_printer(self):
        with self.assertRaises(UserError):
            self.env["device.bridge"].get_test_print_payload(self.scanner.code)
