from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestReportPickingEpl(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env[
            "report.stock_picking_epl_webusb.report_picking_epl"
        ]
        cls.main_partner = cls.env["res.partner"].create(
            {
                "name": "Main Shipping Contact",
                "phone": "0212-5550101",
                "mobile": "0414-5550101",
            }
        )
        cls.delivery_partner = cls.env["res.partner"].create(
            {
                "name": "Delivery Contact",
                "parent_id": cls.main_partner.id,
                "type": "delivery",
            }
        )

    def test_phone_falls_back_to_main_partner(self):
        self.assertEqual(
            self.report._partner_phone(self.delivery_partner),
            self.main_partner.phone,
        )

    def test_mobile_falls_back_to_main_partner(self):
        self.main_partner.phone = False

        self.assertEqual(
            self.report._partner_phone(self.delivery_partner),
            self.main_partner.mobile,
        )

    def test_delivery_contact_phone_has_priority(self):
        self.delivery_partner.mobile = "0424-5550101"

        self.assertEqual(
            self.report._partner_phone(self.delivery_partner),
            self.delivery_partner.mobile,
        )

    def test_phones_text_shows_phone_next_to_mobile(self):
        self.assertEqual(
            self.report._partner_phones_text(self.main_partner),
            "0212-5550101 0414-5550101",
        )

    def test_phones_text_uses_parent_phone_and_delivery_mobile(self):
        self.delivery_partner.mobile = "0424-5550101"

        self.assertEqual(
            self.report._partner_phones_text(self.delivery_partner),
            "0212-5550101 0424-5550101",
        )
