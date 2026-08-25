from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestInterCompanySalePurchaseCommon


@tagged("post_install", "-at_install")
class TestIcSecurity(TestInterCompanySalePurchaseCommon):

    def test_ic_user_missing_groups_raises_clear_error(self):
        weak_user = self.env["res.users"].create(
            {
                "name": "IC Weak",
                "login": "ic_weak_user",
                "company_id": self.company_b.id,
                "company_ids": [(6, 0, [self.company_b.id])],
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        self.company_b.ic_user_id = weak_user
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
                                "price_unit": 10.0,
                                "product_uom": self.product.uom_id.id,
                            },
                        )
                    ],
                }
            )
        )
        with self.assertRaises(UserError) as error:
            po.with_company(self.company_a).button_confirm()
        self.assertIn("missing access", str(error.exception).lower())

    def test_buyer_without_vendor_company_gets_price_and_stock(self):
        buyer = self.env["res.users"].create(
            {
                "name": "Buyer Only A",
                "login": "buyer_only_a",
                "company_id": self.company_a.id,
                "company_ids": [(6, 0, [self.company_a.id])],
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("purchase.group_purchase_user").id,
                            self.env.ref("stock.group_stock_user").id,
                        ],
                    )
                ],
            }
        )
        self.product.with_company(self.company_b).list_price = 88.0
        customer = self.company_a.partner_id.with_company(self.company_b)
        pricelist = customer.property_product_pricelist
        if pricelist:
            self.env["product.pricelist.item"].sudo().create(
                {
                    "pricelist_id": pricelist.id,
                    "product_id": self.product.id,
                    "compute_price": "fixed",
                    "fixed_price": 88.0,
                    "company_id": self.company_b.id,
                }
            )
        wh_b = self.company_b.ic_warehouse_id
        self.env["stock.quant"].with_company(self.company_b).sudo().create(
            {
                "product_id": self.product.id,
                "location_id": wh_b.lot_stock_id.id,
                "inventory_quantity": 7.0,
            }
        ).action_apply_inventory()

        po = (
            self.env["purchase.order"]
            .with_user(buyer)
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
        self.assertAlmostEqual(po.order_line.price_unit, 88.0)
        self.assertAlmostEqual(po.order_line.ic_qty_available, 7.0)
