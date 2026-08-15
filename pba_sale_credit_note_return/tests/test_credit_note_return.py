from odoo import Command
from odoo.tests import tagged

from odoo.addons.sale_stock.tests.common import TestSaleStockCommon


@tagged("post_install", "-at_install")
class TestCreditNoteReturn(TestSaleStockCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_consu = cls.company_data["product_delivery_no"]
        cls.product_order = cls.env["product.product"].create({
            "name": "Order policy storable",
            "type": "consu",
            "is_storable": True,
            "list_price": 100.0,
            "invoice_policy": "order",
            "taxes_id": False,
        })
        cls.product_storable = cls.env["product.product"].create({
            "name": "Storable return test",
            "type": "consu",
            "is_storable": True,
            "list_price": 100.0,
            "invoice_policy": "delivery",
            "taxes_id": False,
        })
        warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.return_picking_type = cls.env["stock.picking.type"].create({
            "name": "DEVOLUCIONES TEST",
            "code": "incoming",
            "sequence_code": "DEVTEST",
            "warehouse_id": warehouse.id,
            "default_location_src_id": cls.env.ref("stock.stock_location_customers").id,
            "default_location_dest_id": warehouse.lot_stock_id.id,
        })
        cls.company_fallback_return_type = cls.env["stock.picking.type"].create({
            "name": "FALLBACK NC RETURN",
            "code": "incoming",
            "sequence_code": "NCFALL",
            "warehouse_id": warehouse.id,
            "default_location_src_id": cls.env.ref("stock.stock_location_customers").id,
            "default_location_dest_id": warehouse.lot_stock_id.id,
        })
        cls.env.company.pba_credit_note_return_picking_type_id = (
            cls.company_fallback_return_type
        )
        warehouse.out_type_id.return_picking_type_id = cls.return_picking_type
        for product in (cls.product_order, cls.product_storable):
            cls.env["stock.quant"]._update_available_quantity(
                product, warehouse.lot_stock_id, 100.0
            )
        cls.warehouse = warehouse

    def _get_new_sale_order(self, product=None, amount=10.0):
        product = product or self.product_consu
        return self.env["sale.order"].create({
            "partner_id": self.partner_a.id,
            "partner_invoice_id": self.partner_a.id,
            "partner_shipping_id": self.partner_a.id,
            "order_line": [Command.create({
                "name": product.name,
                "product_id": product.id,
                "product_uom_qty": amount,
                "product_uom": product.uom_id.id,
                "price_unit": product.list_price,
            })],
            "pricelist_id": self.company_data["default_pricelist"].id,
        })

    def _deliver(self, sale_order, qty=None):
        picking = sale_order.picking_ids.filtered(
            lambda p: p.picking_type_code == "outgoing" and p.state != "cancel"
        )[:1]
        deliver_qty = qty if qty is not None else sale_order.order_line.product_uom_qty
        picking.move_ids.write({
            "quantity": deliver_qty,
            "picked": True,
        })
        picking.button_validate()
        return picking

    def _deliver_and_invoice(self, sale_order, qty=None):
        sale_order.action_confirm()
        picking = self._deliver(sale_order, qty=qty)
        invoice = sale_order._create_invoices()
        invoice.action_post()
        return picking, invoice

    def _create_and_post_credit_note(self, invoice, quantity=None):
        reversal = self.env["account.move.reversal"].with_context(
            active_model="account.move",
            active_ids=invoice.ids,
        ).create({
            "reason": "Test refund",
            "journal_id": invoice.journal_id.id,
        })
        action = reversal.refund_moves()
        credit_note = self.env["account.move"].browse(action["res_id"])
        if quantity is not None:
            product_lines = credit_note.invoice_line_ids.filtered(
                lambda line: line.display_type == "product"
            )
            product_lines.write({"quantity": quantity})
        credit_note.action_post()
        return credit_note

    def test_credit_note_creates_return_picking_consu(self):
        sale_order = self._get_new_sale_order(product=self.product_consu)
        picking, invoice = self._deliver_and_invoice(sale_order)
        credit_note = self._create_and_post_credit_note(invoice)
        return_pickings = credit_note.credit_note_return_picking_ids
        self.assertEqual(len(return_pickings), 1)
        self.assertEqual(return_pickings.return_id, picking)
        self.assertEqual(return_pickings.picking_type_id, self.return_picking_type)
        self.assertEqual(return_pickings.move_ids.product_uom_qty, 10)
        self.assertTrue(return_pickings.move_ids.to_refund)

    def test_credit_note_creates_return_picking_storable(self):
        sale_order = self._get_new_sale_order(product=self.product_storable)
        picking, invoice = self._deliver_and_invoice(sale_order)
        credit_note = self._create_and_post_credit_note(invoice)
        return_pickings = credit_note.credit_note_return_picking_ids
        self.assertEqual(len(return_pickings), 1)
        self.assertEqual(return_pickings.picking_type_id, self.return_picking_type)

    def test_partial_credit_note_creates_partial_return(self):
        sale_order = self._get_new_sale_order(amount=10.0)
        picking, invoice = self._deliver_and_invoice(sale_order)
        credit_note = self._create_and_post_credit_note(invoice, quantity=4)
        return_picking = credit_note.credit_note_return_picking_ids
        self.assertEqual(len(return_picking), 1)
        self.assertEqual(return_picking.picking_type_id, self.return_picking_type)
        self.assertEqual(return_picking.move_ids.product_uom_qty, 4)

    def test_validate_return_sets_ordered_qty_to_delivered(self):
        sale_order = self._get_new_sale_order()
        _picking, invoice = self._deliver_and_invoice(sale_order)
        credit_note = self._create_and_post_credit_note(invoice)
        return_picking = credit_note.credit_note_return_picking_ids
        self.assertTrue(return_picking)
        return_picking.move_ids.write({"quantity": 10, "picked": True})
        return_picking.button_validate()
        self.assertEqual(sale_order.order_line.qty_delivered, 0)
        self.assertEqual(sale_order.order_line.product_uom_qty, 0)

    def test_validate_partial_return_keeps_remaining_ordered_qty(self):
        sale_order = self._get_new_sale_order(amount=10.0)
        _picking, invoice = self._deliver_and_invoice(sale_order)
        credit_note = self._create_and_post_credit_note(invoice, quantity=3)
        return_picking = credit_note.credit_note_return_picking_ids
        return_picking.move_ids.write({"quantity": 3, "picked": True})
        return_picking.button_validate()
        self.assertEqual(sale_order.order_line.qty_delivered, 7)
        self.assertEqual(sale_order.order_line.product_uom_qty, 7)

    def test_service_credit_note_does_not_create_return(self):
        product = self.company_data["product_service_delivery"]
        sale_order = self.env["sale.order"].create({
            "partner_id": self.partner_a.id,
            "order_line": [Command.create({
                "name": product.name,
                "product_id": product.id,
                "product_uom_qty": 1,
                "price_unit": 50,
            })],
        })
        sale_order.action_confirm()
        sale_order.order_line.qty_delivered = 1
        invoice = sale_order._create_invoices()
        invoice.action_post()
        credit_note = self._create_and_post_credit_note(invoice)
        self.assertFalse(credit_note.credit_note_return_picking_ids)

    def test_credit_note_before_delivery_creates_configured_return(self):
        """Invoice policy order: credit note before delivery still creates DEVOLUCIONES."""
        sale_order = self._get_new_sale_order(product=self.product_order, amount=1.0)
        sale_order.action_confirm()
        invoice = sale_order._create_invoices()
        invoice.action_post()
        credit_note = self._create_and_post_credit_note(invoice)
        return_picking = credit_note.credit_note_return_picking_ids
        self.assertEqual(len(return_picking), 1)
        self.assertEqual(return_picking.picking_type_id, self.return_picking_type)
        self.assertEqual(return_picking.picking_type_id.code, "incoming")
        return_picking.move_ids.write({"quantity": 1, "picked": True})
        return_picking.button_validate()
        self.assertEqual(sale_order.order_line.qty_delivered, 0)
        self.assertEqual(sale_order.order_line.product_uom_qty, 0)

    def test_credit_note_uses_original_operation_return_type(self):
        sale_order = self._get_new_sale_order(product=self.product_storable)
        picking, invoice = self._deliver_and_invoice(sale_order)
        self.assertEqual(
            picking.picking_type_id.return_picking_type_id, self.return_picking_type
        )
        credit_note = self._create_and_post_credit_note(invoice)
        return_picking = credit_note.credit_note_return_picking_ids
        self.assertEqual(return_picking.picking_type_id, self.return_picking_type)
        self.assertNotEqual(
            return_picking.picking_type_id, self.company_fallback_return_type
        )

    def test_credit_note_falls_back_to_company_return_type(self):
        self.warehouse.out_type_id.return_picking_type_id = False
        sale_order = self._get_new_sale_order(product=self.product_storable)
        _picking, invoice = self._deliver_and_invoice(sale_order)
        credit_note = self._create_and_post_credit_note(invoice)
        return_picking = credit_note.credit_note_return_picking_ids
        self.assertEqual(
            return_picking.picking_type_id, self.company_fallback_return_type
        )

    def test_receipt_return_keeps_original_operation_return_type(self):
        """Reception returns must not use the company NC return type."""
        product = self.product_storable
        receipt_type = self.warehouse.in_type_id
        receipt_return_type = self.env["stock.picking.type"].create({
            "name": "RETURN TO VENDOR TEST",
            "code": "outgoing",
            "sequence_code": "RTV",
            "warehouse_id": self.warehouse.id,
            "default_location_src_id": self.warehouse.lot_stock_id.id,
            "default_location_dest_id": self.env.ref("stock.stock_location_suppliers").id,
        })
        receipt_type.return_picking_type_id = receipt_return_type
        receipt = self.env["stock.picking"].create({
            "picking_type_id": receipt_type.id,
            "location_id": self.env.ref("stock.stock_location_suppliers").id,
            "location_dest_id": self.warehouse.lot_stock_id.id,
            "move_ids": [Command.create({
                "name": product.name,
                "product_id": product.id,
                "product_uom_qty": 2,
                "product_uom": product.uom_id.id,
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": self.warehouse.lot_stock_id.id,
            })],
        })
        receipt.action_confirm()
        receipt.move_ids.write({"quantity": 2, "picked": True})
        receipt.button_validate()
        wizard = self.env["stock.return.picking"].with_context(
            active_id=receipt.id,
            active_ids=receipt.ids,
            active_model="stock.picking",
        ).create({"picking_id": receipt.id})
        wizard.product_return_moves.quantity = 2
        action = wizard.action_create_returns()
        return_picking = self.env["stock.picking"].browse(action["res_id"])
        self.assertEqual(return_picking.picking_type_id, receipt_return_type)
        self.assertNotEqual(
            return_picking.picking_type_id, self.company_fallback_return_type
        )
        self.assertNotEqual(return_picking.picking_type_id, self.return_picking_type)
