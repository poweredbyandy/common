from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestPartnerCompanyPropertySync(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_2_data = cls.setup_other_company()
        cls.company_2 = cls.company_2_data["company"]
        cls.env.company.account_use_credit_limit = True
        cls.company_2.account_use_credit_limit = True

        cls.global_pricelist = cls.env["product.pricelist"].create({
            "name": "Lista global sync",
            "company_id": False,
        })
        cls.company_1_pricelist = cls.env["product.pricelist"].create({
            "name": "Lista compañía 1",
            "company_id": cls.env.company.id,
        })
        cls.company_2_pricelist = cls.env["product.pricelist"].create({
            "name": "Lista compañía 2",
            "company_id": cls.company_2.id,
        })

        cls.global_payment_term = cls.env["account.payment.term"].create({
            "name": "30 días global",
            "company_id": False,
            "line_ids": [
                Command.create({"value": "percent", "value_amount": 100.0, "nb_days": 30}),
            ],
        })
        cls.company_1_payment_term = cls.env["account.payment.term"].create({
            "name": "15 días compañía 1",
            "company_id": cls.env.company.id,
            "line_ids": [
                Command.create({"value": "percent", "value_amount": 100.0, "nb_days": 15}),
            ],
        })

        cls.partner = cls.env["res.partner"].create({"name": "Cliente multi compañía"})

    def _wizard(self, **values):
        return self.env["res.partner.company.property.sync.wizard"].create({
            "source_company_id": self.env.company.id,
            "target_company_ids": [Command.set([self.company_2.id])],
            "partner_ids": [Command.set([self.partner.id])],
            **values,
        })

    def test_sync_fields_are_discovered_dynamically(self):
        sync_fields = self.env["res.partner"]._get_partner_company_sync_field_names()
        self.assertIn("credit_limit", sync_fields)
        self.assertIn("property_payment_term_id", sync_fields)
        self.assertIn("specific_property_product_pricelist", sync_fields)

    def test_auto_sync_global_pricelist(self):
        self.partner.with_company(self.env.company).write({
            "specific_property_product_pricelist": self.global_pricelist.id,
        })
        partner_company_2 = self.partner.with_company(self.company_2)
        self.assertEqual(
            partner_company_2.specific_property_product_pricelist,
            self.global_pricelist,
        )

    def test_auto_sync_does_not_copy_company_specific_pricelist(self):
        self.partner.with_company(self.company_2).with_context(
            skip_partner_company_sync=True,
        ).write({
            "specific_property_product_pricelist": self.company_2_pricelist.id,
        })
        self.partner.with_company(self.env.company).write({
            "specific_property_product_pricelist": self.company_1_pricelist.id,
        })
        partner_company_2 = self.partner.with_company(self.company_2)
        self.assertEqual(
            partner_company_2.specific_property_product_pricelist,
            self.company_2_pricelist,
        )

    def test_auto_sync_global_payment_term_and_credit_limit(self):
        self.partner.with_company(self.env.company).write({
            "property_payment_term_id": self.global_payment_term.id,
            "credit_limit": 5000.0,
        })
        partner_company_2 = self.partner.with_company(self.company_2)
        self.assertEqual(partner_company_2.property_payment_term_id, self.global_payment_term)
        self.assertEqual(partner_company_2.credit_limit, 5000.0)

    def test_auto_sync_skips_company_specific_payment_term(self):
        self.partner.with_company(self.company_2).with_context(
            skip_partner_company_sync=True,
        ).write({
            "property_payment_term_id": self.global_payment_term.id,
        })
        self.partner.with_company(self.env.company).write({
            "property_payment_term_id": self.company_1_payment_term.id,
        })
        partner_company_2 = self.partner.with_company(self.company_2)
        self.assertEqual(partner_company_2.property_payment_term_id, self.global_payment_term)

    def test_auto_sync_via_property_product_pricelist(self):
        self.partner.with_company(self.env.company).write({
            "property_product_pricelist": self.global_pricelist.id,
        })
        partner_company_2 = self.partner.with_company(self.company_2)
        self.assertEqual(partner_company_2.property_product_pricelist, self.global_pricelist)

    def test_wizard_sync_from_source_company(self):
        self.partner.with_company(self.env.company).write({
            "specific_property_product_pricelist": self.global_pricelist.id,
            "property_payment_term_id": self.global_payment_term.id,
            "credit_limit": 2500.0,
        })
        self.partner.with_company(self.company_2).with_context(
            skip_partner_company_sync=True,
        ).write({
            "specific_property_product_pricelist": self.company_2_pricelist.id,
            "credit_limit": 100.0,
        })

        wizard = self._wizard()
        wizard.action_sync()

        partner_company_2 = self.partner.with_company(self.company_2)
        self.assertEqual(partner_company_2.specific_property_product_pricelist, self.global_pricelist)
        self.assertEqual(partner_company_2.property_payment_term_id, self.global_payment_term)
        self.assertEqual(partner_company_2.credit_limit, 2500.0)

    def test_wizard_skips_invalid_reference(self):
        self.partner.with_company(self.env.company).write({
            "specific_property_product_pricelist": self.company_1_pricelist.id,
            "credit_limit": 900.0,
        })
        self.partner.with_company(self.company_2).with_context(
            skip_partner_company_sync=True,
        ).write({
            "specific_property_product_pricelist": self.company_2_pricelist.id,
            "credit_limit": 100.0,
        })

        wizard = self._wizard()
        wizard.action_sync()

        partner_company_2 = self.partner.with_company(self.company_2)
        self.assertEqual(partner_company_2.specific_property_product_pricelist, self.company_2_pricelist)
        self.assertEqual(partner_company_2.credit_limit, 900.0)

    def test_edit_from_second_company_syncs_first_company(self):
        self.partner.with_company(self.company_2).write({
            "property_payment_term_id": self.global_payment_term.id,
            "credit_limit": 1200.0,
        })
        partner_company_1 = self.partner.with_company(self.env.company)
        self.assertEqual(partner_company_1.property_payment_term_id, self.global_payment_term)
        self.assertEqual(partner_company_1.credit_limit, 1200.0)
