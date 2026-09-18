from lxml import etree

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPurchaseReceiptStatusColor(TransactionCase):
    def test_list_receipt_status_uses_status_colors(self):
        arch = self.env["purchase.order"].get_view(
            view_id=self.env.ref("purchase.purchase_order_view_tree").id,
            view_type="list",
        )["arch"]
        field = etree.fromstring(arch).xpath("//field[@name='receipt_status']")[0]
        self.assertEqual(field.get("decoration-success"), "receipt_status == 'full'")
        self.assertEqual(field.get("decoration-warning"), "receipt_status == 'partial'")
        self.assertEqual(field.get("decoration-info"), "receipt_status == 'pending'")
        self.assertFalse(field.get("decoration-danger"))
