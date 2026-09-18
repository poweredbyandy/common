from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests import TransactionCase, tagged

from odoo.addons.report_escpos_inventory.report.report_stock_picking_dispatch_escpos import (
    _invoice_for_picking,
    _invoice_ref,
)


@tagged("post_install", "-at_install")
class TestDispatchInvoiceRef(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Dispatch Customer",
                "company_id": cls.env.company.id,
            }
        )
        cls.products = cls.env["product.product"]
        for index in range(4):
            cls.products |= cls.env["product.product"].create(
                {
                    "name": "Dispatch Product %s" % (index + 1),
                    "default_code": "DISP-%s" % (index + 1),
                    "type": "consu",
                    "is_storable": True,
                    "invoice_policy": "order",
                    "list_price": 10.0,
                    "company_id": cls.env.company.id,
                }
            )
        warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        for product in cls.products:
            cls.env["stock.quant"]._update_available_quantity(
                product, warehouse.lot_stock_id, 50.0
            )

    def _create_split_sale(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_uom_qty": 1,
                            "price_unit": 10.0,
                        }
                    )
                    for product in self.products
                ],
            }
        )
        order.action_confirm()
        picking = order.picking_ids.filtered(
            lambda rec: rec.picking_type_code == "outgoing"
        )
        self.assertEqual(len(picking), 1)
        first_moves = picking.move_ids.filtered(
            lambda move: move.product_id in self.products[:2]
        )
        second_moves = picking.move_ids - first_moves
        picking2 = picking.copy({"move_ids": False, "move_line_ids": False})
        second_moves.write({"picking_id": picking2.id})
        if second_moves.move_line_ids:
            second_moves.move_line_ids.write({"picking_id": picking2.id})
        return order, picking, picking2

    def _invoice_picking_products(self, order, picking):
        sale_lines = picking.move_ids.mapped("sale_line_id")
        return self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": order.partner_id.id,
                "invoice_origin": order.name,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": line.product_id.id,
                            "quantity": line.product_uom_qty,
                            "price_unit": line.price_unit,
                            "sale_line_ids": [Command.set(line.ids)],
                        }
                    )
                    for line in sale_lines
                ],
            }
        )

    def test_invoice_ref_before_validate_matches_each_picking(self):
        order, picking1, picking2 = self._create_split_sale()
        self.assertNotEqual(picking1.state, "done")
        self.assertNotEqual(picking2.state, "done")
        invoice1 = self._invoice_picking_products(order, picking1)
        invoice2 = self._invoice_picking_products(order, picking2)
        self.assertFalse(picking1.invoice_ids)
        self.assertFalse(picking2.invoice_ids)
        self.assertEqual(_invoice_for_picking(picking1), invoice1)
        self.assertEqual(_invoice_for_picking(picking2), invoice2)
        try:
            (invoice1 + invoice2).action_post()
        except (UserError, ValidationError):
            return
        self.assertNotEqual(invoice1.name, invoice2.name)
        self.assertEqual(_invoice_ref(picking1), invoice1.name)
        self.assertEqual(_invoice_ref(picking2), invoice2.name)
        report = self.env["report.report_escpos_inventory.dispatch_escpos_doc"]
        header1, _count1 = report._header_block(picking1, 1, 1, "\n")
        header2, _count2 = report._header_block(picking2, 1, 1, "\n")
        self.assertIn(invoice1.name, header1)
        self.assertNotIn(invoice2.name, header1)
        self.assertIn(invoice2.name, header2)
        self.assertNotIn(invoice1.name, header2)
