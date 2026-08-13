from odoo.addons.stock.tests.common import TestStockCommon
from odoo.fields import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPbaStockBarcodeKanbanInfo(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        tax = cls.env["account.tax"].search(
            [("type_tax_use", "=", "sale"), ("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        cls.partner = cls.env["res.partner"].create({"name": "PBA barcode partner"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "PBA barcode product",
                "taxes_id": [Command.set(tax.ids)] if tax else [Command.clear()],
            }
        )
        cls.sale = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "payment_term_id": False,
                "order_line": [
                    Command.create(
                        {
                            "product_id": cls.product.id,
                            "product_uom_qty": 1,
                        }
                    )
                ],
            }
        )

    def _create_outgoing_picking(self, sale):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.env.ref("stock.picking_type_out").id,
                "location_id": self.env.ref("stock.stock_location_stock").id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                "partner_id": self.partner.id,
            }
        )
        picking.sale_id = sale
        return picking

    def test_sale_without_payment_term_shows_de_contado(self):
        picking = self._create_outgoing_picking(self.sale)
        self.assertIn(self.sale.name, picking.pba_barcode_sale_name)
        self.assertEqual(picking.pba_barcode_payment_term_label, "De Contado")
        self.assertEqual(picking.pba_barcode_invoice_payment_state, "none")
        self.assertEqual(picking.pba_barcode_invoice_payment_label, "Sin factura")
        self.assertEqual(picking.pba_barcode_kanban_tone, "immediate_unpaid")
        self.assertEqual(picking.pba_barcode_partner_vat, self.partner.vat or False)

    def test_sale_with_payment_term_shows_term_name(self):
        term = self.env["account.payment.term"].create(
            {
                "name": "15 dias",
                "line_ids": [
                    Command.clear(),
                    Command.create(
                        {
                            "value": "percent",
                            "value_amount": 100,
                            "nb_days": 15,
                        }
                    ),
                ],
            }
        )
        self.sale.payment_term_id = term
        picking = self._create_outgoing_picking(self.sale)
        self.assertTrue(picking.pba_barcode_payment_term_label.startswith("\u2060"))
        self.assertTrue(picking.pba_barcode_payment_term_label.endswith(term.display_name))
        self.assertEqual(picking.pba_barcode_kanban_tone, "credit")

    def test_immediate_zero_days_unpaid_uses_red_tone(self):
        term = self.env["account.payment.term"].create({"name": "Contado 0 dias"})
        self.sale.payment_term_id = term
        picking = self._create_outgoing_picking(self.sale)
        self.assertTrue(picking._pba_payment_term_is_immediate(term))
        self.assertEqual(picking.pba_barcode_kanban_tone, "immediate_unpaid")

    def test_immediate_paid_has_no_tone(self):
        picking = self._create_outgoing_picking(self.sale)
        tone = picking._pba_barcode_kanban_tone(False, "paid")
        self.assertFalse(tone)

    def test_payment_term_write_notifies_barcode_pickings(self):
        picking = self._create_outgoing_picking(self.sale)
        calls = []

        def _notify(self_pickings):
            calls.append(self_pickings.ids)

        self.patch(
            type(self.env["stock.picking"]),
            "_pba_notify_barcode_available",
            _notify,
        )
        term = self.env["account.payment.term"].create({"name": "30 dias"})
        self.sale.payment_term_id = term
        self.assertTrue(calls)
        self.assertIn(picking.id, calls[0])


@tagged("post_install", "-at_install")
class TestPbaStockBarcodePickingReload(TestStockCommon):
    def _locations(self):
        return (
            self.env["stock.location"].browse(self.stock_location),
            self.env["stock.location"].browse(self.customer_location),
        )

    def _transfer_reason(self):
        reason_model = self.env["l10n_ve.stock.transfer.reason"]
        reason = reason_model.search([], limit=1)
        if reason:
            return reason
        return reason_model.create({"name": "Test motivo"})

    def _picking_vals(self, stock_location, customer_location, extra=None):
        vals = {
            "picking_type_id": self.picking_type_out,
            "location_id": stock_location.id,
            "location_dest_id": customer_location.id,
            "l10n_ve_internal_transfer_reason_id": self._transfer_reason().id,
        }
        if extra:
            vals.update(extra)
        return vals

    def _patch_bus(self):
        notifications = []

        def _bus_send(self, notification_type, message, /, *, subchannel=None):
            notifications.append((notification_type, message))

        self.patch(
            type(self.env.ref("stock.group_stock_user")),
            "_bus_send",
            _bus_send,
        )
        return notifications

    def test_move_assign_notifies_like_sale_confirm(self):
        stock_location, customer_location = self._locations()
        self.env["stock.quant"]._update_available_quantity(
            self.productA, stock_location, 10
        )
        picking = self.env["stock.picking"].create(
            self._picking_vals(stock_location, customer_location)
        )
        move = self.env["stock.move"].create(
            {
                "name": self.productA.name,
                "product_id": self.productA.id,
                "product_uom": self.productA.uom_id.id,
                "product_uom_qty": 1,
                "picking_id": picking.id,
                "location_id": stock_location.id,
                "location_dest_id": customer_location.id,
            }
        )
        move._action_confirm()
        self.assertNotEqual(picking.state, "assigned")
        notifications = self._patch_bus()
        move._action_assign()
        self.assertEqual(picking.state, "assigned")
        assigned = [
            payload
            for ntype, payload in notifications
            if ntype == "pba.stock.picking/available"
        ]
        self.assertTrue(
            assigned,
            "Bus notification must fire when moves are reserved without picking.action_assign",
        )
        self.assertEqual(assigned[0]["picking_type_id"], picking.picking_type_id.id)
