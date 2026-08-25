from odoo.tests import tagged

from .common import TestInterCompanySalePurchaseCommon


@tagged("post_install", "-at_install")
class TestIcPoPriceStock(TestInterCompanySalePurchaseCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product.with_company(cls.company_b).list_price = 175.0
        customer = cls.company_a.partner_id.with_company(cls.company_b)
        pricelist = customer.property_product_pricelist
        if pricelist:
            cls.env["product.pricelist.item"].create(
                {
                    "pricelist_id": pricelist.id,
                    "product_id": cls.product.id,
                    "compute_price": "fixed",
                    "fixed_price": 175.0,
                    "company_id": cls.company_b.id,
                }
            )
        wh_b = cls.company_b.ic_warehouse_id
        cls.env["stock.quant"].with_company(cls.company_b).create(
            {
                "product_id": cls.product.id,
                "location_id": wh_b.lot_stock_id.id,
                "inventory_quantity": 42.0,
            }
        ).action_apply_inventory()

    def test_po_line_uses_vendor_sale_price(self):
        po = (
            self.env["purchase.order"]
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
                                "product_qty": 1.0,
                                "product_uom": self.product.uom_id.id,
                            },
                        )
                    ],
                }
            )
        )
        self.assertTrue(po.is_intercompany_vendor)
        self.assertAlmostEqual(po.order_line.price_unit, 175.0)

    def test_po_line_shows_vendor_qty(self):
        po = (
            self.env["purchase.order"]
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
                                "product_qty": 1.0,
                                "price_unit": 1.0,
                                "product_uom": self.product.uom_id.id,
                            },
                        )
                    ],
                }
            )
        )
        self.assertAlmostEqual(po.order_line.ic_qty_available, 42.0)
