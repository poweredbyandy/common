from odoo.tests import tagged

from .common import TestInterCompanySalePurchaseCommon


@tagged("post_install", "-at_install")
class TestIcSaleForecastQty(TestInterCompanySalePurchaseCommon):

    def test_sale_line_free_qty_other_companies(self):
        wh_b = self.company_b.ic_warehouse_id
        self.env["stock.quant"].with_company(self.company_b).sudo().create(
            {
                "product_id": self.product.id,
                "location_id": wh_b.lot_stock_id.id,
                "inventory_quantity": 25.0,
            }
        ).action_apply_inventory()
        so = (
            self.env["sale.order"]
            .with_company(self.company_a)
            .create(
                {
                    "partner_id": self.company_b.partner_id.id,
                    "company_id": self.company_a.id,
                    "order_line": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.product.id,
                                "name": self.product.name,
                                "product_uom_qty": 1.0,
                                "price_unit": 10.0,
                                "product_uom": self.product.uom_id.id,
                            },
                        )
                    ],
                }
            )
        )
        rows = {row["company_id"]: row["free_qty"] for row in so.order_line.ic_free_qty_by_company}
        self.assertIn(self.company_b.id, rows)
        self.assertAlmostEqual(rows[self.company_b.id], 25.0)
        self.assertNotIn(self.company_a.id, rows)
