from odoo.fields import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestEplDispatchInvoiceRef(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sale_installed = "sale.order" in cls.env
        if not cls.sale_installed:
            return
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "EPL Dispatch Customer",
                "company_id": cls.env.company.id,
            }
        )
        cls.products = cls.env["product.product"]
        for index in range(4):
            cls.products |= cls.env["product.product"].create(
                {
                    "name": "EPL Dispatch Product %s" % (index + 1),
                    "default_code": "EPL-DISP-%s" % (index + 1),
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

    def test_epl_invoice_ref_before_validate_matches_each_picking(self):
        if not self.sale_installed:
            self.skipTest("sale is not installed")
        order, picking1, picking2 = self._create_split_sale()
        self.assertNotEqual(picking1.state, "done")
        self.assertNotEqual(picking2.state, "done")
        invoice1 = self._invoice_picking_products(order, picking1)
        invoice2 = self._invoice_picking_products(order, picking2)
        self.assertEqual(picking1._dispatch_invoice_for_picking(), invoice1)
        self.assertEqual(picking2._dispatch_invoice_for_picking(), invoice2)
        report = self.env["report.stock_picking_epl_webusb.report_picking_epl"]
        self.assertEqual(
            report._invoice_ref(picking1),
            invoice1.name or invoice1.payment_reference or "",
        )
        self.assertEqual(
            report._invoice_ref(picking2),
            invoice2.name or invoice2.payment_reference or "",
        )
