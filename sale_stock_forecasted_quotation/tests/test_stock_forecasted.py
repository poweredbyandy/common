from odoo import Command
from odoo.addons.stock.tests.test_report import TestReportsCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestForecastedDraftSaleOrders(TestReportsCommon):
    def test_draft_sale_orders_are_split_with_partner(self):
        partner_a = self.env["res.partner"].create({"name": "Cliente A"})
        partner_b = self.env["res.partner"].create({"name": "Cliente B"})
        so_a = self.env["sale.order"].create(
            {
                "partner_id": partner_a.id,
                "order_line": [
                    Command.create(
                        {
                            "name": self.product.name,
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                        }
                    ),
                ],
            }
        )
        so_b = self.env["sale.order"].create(
            {
                "partner_id": partner_b.id,
                "order_line": [
                    Command.create(
                        {
                            "name": self.product.name,
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                        }
                    ),
                ],
            }
        )

        _report_values, docs, _lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids
        )
        draft_orders = docs["draft_sale_orders"]
        self.assertEqual(docs["draft_sale_qty"], 2)
        self.assertEqual(len(draft_orders), 2)
        by_id = {order["id"]: order for order in draft_orders}
        self.assertEqual(by_id[so_a.id]["qty"], 1)
        self.assertEqual(by_id[so_a.id]["name"], so_a.name)
        self.assertEqual(by_id[so_a.id]["partner_name"], "Cliente A")
        self.assertEqual(by_id[so_b.id]["qty"], 1)
        self.assertEqual(by_id[so_b.id]["name"], so_b.name)
        self.assertEqual(by_id[so_b.id]["partner_name"], "Cliente B")

    def test_same_quotation_keeps_its_quantity(self):
        partner = self.env["res.partner"].create({"name": "Cliente Unico"})
        so = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [
                    Command.create(
                        {
                            "name": self.product.name,
                            "product_id": self.product.id,
                            "product_uom_qty": 2,
                        }
                    ),
                ],
            }
        )

        _report_values, docs, _lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids
        )
        draft_orders = docs["draft_sale_orders"]
        self.assertEqual(len(draft_orders), 1)
        self.assertEqual(draft_orders[0]["id"], so.id)
        self.assertEqual(draft_orders[0]["qty"], 2)
        self.assertEqual(draft_orders[0]["partner_name"], "Cliente Unico")
