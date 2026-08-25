from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestInterCompanySalePurchaseCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.company_data["company"]
        cls.company_b = cls.setup_other_company()["company"]

        cls.product = cls.env["product.product"].create(
            {
                "name": "IC Product",
                "type": "consu",
                "is_storable": True,
                "list_price": 100.0,
                "standard_price": 50.0,
                "categ_id": cls.env.ref("product.product_category_all").id,
                "company_id": False,
                "taxes_id": False,
                "supplier_taxes_id": False,
            }
        )

        warehouse_a = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company_a.id)], limit=1
        )
        warehouse_b = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company_b.id)], limit=1
        )
        receipt_a = cls.env["stock.picking.type"].search(
            [("company_id", "=", cls.company_a.id), ("code", "=", "incoming")],
            limit=1,
        )
        receipt_b = cls.env["stock.picking.type"].search(
            [("company_id", "=", cls.company_b.id), ("code", "=", "incoming")],
            limit=1,
        )
        journal_a = cls.env["account.journal"].search(
            [("company_id", "=", cls.company_a.id), ("type", "=", "purchase")],
            limit=1,
        )
        journal_b = cls.env["account.journal"].search(
            [("company_id", "=", cls.company_b.id), ("type", "=", "purchase")],
            limit=1,
        )

        ic_user = cls.env.ref("base.user_admin")
        ic_user.company_ids |= cls.company_a | cls.company_b
        cls.company_a.write(
            {
                "ic_so_from_po": True,
                "ic_po_from_so": True,
                "ic_so_state": "draft",
                "ic_po_state": "draft",
                "ic_picking_mode": "none",
                "ic_invoice_mode": "none",
                "ic_user_id": ic_user.id,
                "ic_warehouse_id": warehouse_a.id,
                "ic_receipt_type_id": receipt_a.id,
                "ic_purchase_journal_id": journal_a.id,
                "ic_allow_confirm_ic_purchase": True,
            }
        )
        cls.company_b.write(
            {
                "ic_so_from_po": True,
                "ic_po_from_so": True,
                "ic_so_state": "draft",
                "ic_po_state": "draft",
                "ic_picking_mode": "none",
                "ic_invoice_mode": "none",
                "ic_user_id": ic_user.id,
                "ic_warehouse_id": warehouse_b.id,
                "ic_receipt_type_id": receipt_b.id,
                "ic_purchase_journal_id": journal_b.id,
                "ic_allow_confirm_ic_purchase": True,
            }
        )
