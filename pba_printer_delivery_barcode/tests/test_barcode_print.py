from odoo.fields import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPbaPrinterDeliveryBarcode(TransactionCase):
    def test_barcode_print_uses_delivery_action(self):
        partner = self.env["res.partner"].create({"name": "Barcode POS80 partner"})
        product = self.env["product.product"].create(
            {
                "name": "Barcode POS80 product",
                "is_storable": True,
            }
        )
        dest = self.env.ref("stock.stock_location_customers")
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.env.ref("stock.picking_type_out").id,
                "location_id": self.env.ref("stock.stock_location_stock").id,
                "location_dest_id": dest.id,
                "partner_id": partner.id,
                "move_ids": [
                    Command.create(
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_uom_qty": 1,
                            "product_uom": product.uom_id.id,
                            "location_id": self.env.ref("stock.stock_location_stock").id,
                            "location_dest_id": dest.id,
                        }
                    )
                ],
            }
        )
        action = picking.action_print_pos80()
        self.assertEqual(action["tag"], "pba_printer_delivery_print")
        self.assertEqual(action["params"]["picking_ids"], picking.ids)
