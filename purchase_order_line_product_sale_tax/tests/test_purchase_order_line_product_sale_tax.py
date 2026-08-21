from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestPurchaseOrderLineProductSaleTax(AccountTestInvoicingCommon):
    def _create_order(self, product):
        return self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "order_line": [
                    Command.create(
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_qty": 1.0,
                            "product_uom": product.uom_po_id.id,
                            "price_unit": 10.0,
                        }
                    )
                ],
            }
        )

    def test_line_shows_product_sale_taxes(self):
        self.product_a.taxes_id = self.tax_sale_a
        order = self._create_order(self.product_a)
        self.assertEqual(order.order_line.product_sale_tax_ids, self.tax_sale_a)

    def test_change_line_updates_product_sale_taxes(self):
        self.product_a.taxes_id = self.tax_sale_a
        order = self._create_order(self.product_a)
        order.order_line.product_sale_tax_ids = self.tax_sale_b
        self.assertEqual(self.product_a.taxes_id, self.tax_sale_b)
        self.assertEqual(order.order_line.product_sale_tax_ids, self.tax_sale_b)

    def test_change_does_not_alter_purchase_taxes(self):
        self.product_a.taxes_id = self.tax_sale_a
        self.product_a.supplier_taxes_id = self.tax_purchase_a
        order = self._create_order(self.product_a)
        purchase_taxes = order.order_line.taxes_id
        order.order_line.product_sale_tax_ids = self.tax_sale_b
        self.assertEqual(order.order_line.taxes_id, purchase_taxes)
        self.assertEqual(self.product_a.supplier_taxes_id, self.tax_purchase_a)
