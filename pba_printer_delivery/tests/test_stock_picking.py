import base64

from odoo.fields import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPbaPrinterDelivery(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "POS80 customer",
                "vat": "J-12345678-9",
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "POS80 product",
                "default_code": "POS80-SKU",
                "is_storable": True,
            }
        )
        cls.notify_group = cls.env.ref(
            "pba_bus_picking_notification.group_stock_picking_bus_notify"
        )
        cls.env.user.groups_id = [Command.link(cls.notify_group.id)]
        cls.env.company.pba_pos80_auto_print = True

    def _create_picking(self, picking_type_xmlid, dest_xmlid, **extra):
        picking_type = self.env.ref(picking_type_xmlid)
        location_id = extra.pop(
            "location_id", self.env.ref("stock.stock_location_stock").id
        )
        dest_id = self.env.ref(dest_xmlid).id
        values = {
            "picking_type_id": picking_type.id,
            "location_id": location_id,
            "location_dest_id": dest_id,
            "partner_id": self.partner.id,
            "origin": "SO-POS80",
            "move_ids": [
                Command.create(
                    {
                        "name": self.product.name,
                        "product_id": self.product.id,
                        "product_uom_qty": 2,
                        "product_uom": self.product.uom_id.id,
                        "location_id": location_id,
                        "location_dest_id": dest_id,
                    }
                )
            ],
        }
        values.update(extra)
        return self.env["stock.picking"].create(values)

    def test_ticket_contains_picking_data(self):
        picking = self._create_picking(
            "stock.picking_type_out",
            "stock.stock_location_customers",
        )
        raw = picking._pba_pos80_ticket_bytes()
        text = raw.decode("cp1252", "replace")
        self.assertIn(picking.name, text)
        self.assertIn(self.partner.name, text)
        self.assertIn(self.partner.vat, text)
        self.assertIn("POS80 product", text)
        self.assertIn("SO-POS80", text)
        payload = picking._pba_pos80_ticket_payload()
        self.assertEqual(payload["device_code"], "pos80")
        self.assertEqual(payload["picking_id"], picking.id)
        self.assertEqual(base64.b64decode(payload["data_b64"]), raw)

    def test_action_print_returns_client_action(self):
        picking = self._create_picking(
            "stock.picking_type_out",
            "stock.stock_location_customers",
        )
        action = picking.action_print_pos80()
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "pba_printer_delivery_print")
        self.assertEqual(action["params"]["picking_ids"], picking.ids)
        jobs = self.env["stock.picking"].get_pos80_print_payload(picking.ids)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["picking_id"], picking.id)

    def test_outgoing_autoprint_notifies_when_gateway_missing(self):
        sent = []

        def _bus_send(self, notification_type, message, /, *, subchannel=None):
            sent.append((notification_type, message))

        self.patch(type(self.notify_group), "_bus_send", _bus_send)
        if "device.bridge.gateway" in self.env:
            self.patch(
                type(self.env["device.bridge.gateway"]),
                "send_raw_job",
                lambda self, *args, **kwargs: (_ for _ in ()).throw(
                    Exception("no gateway")
                ),
            )
        picking = self._create_picking(
            "stock.picking_type_out",
            "stock.stock_location_customers",
        )
        print_jobs = [
            payload
            for notify_type, payload in sent
            if notify_type == "pba.stock.picking/print_pos80"
        ]
        self.assertEqual(len(print_jobs), 1)
        self.assertEqual(print_jobs[0]["picking_id"], picking.id)
        self.assertEqual(print_jobs[0]["device_code"], "pos80")

    def test_incoming_picking_does_not_autoprint(self):
        sent = []

        def _bus_send(self, notification_type, message, /, *, subchannel=None):
            sent.append(notification_type)

        self.patch(type(self.notify_group), "_bus_send", _bus_send)
        self._create_picking(
            "stock.picking_type_in",
            "stock.stock_location_stock",
            location_id=self.env.ref("stock.stock_location_suppliers").id,
        )
        self.assertNotIn("pba.stock.picking/print_pos80", sent)

    def test_disabled_company_setting_skips_autoprint(self):
        self.env.company.pba_pos80_auto_print = False
        sent = []

        def _bus_send(self, notification_type, message, /, *, subchannel=None):
            sent.append(notification_type)

        self.patch(type(self.notify_group), "_bus_send", _bus_send)
        self._create_picking(
            "stock.picking_type_out",
            "stock.stock_location_customers",
        )
        self.assertNotIn("pba.stock.picking/print_pos80", sent)
