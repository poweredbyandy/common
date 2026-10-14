# Copyright 2026 andyengit
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestRefMatch(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bank_journal = cls.company_data["default_journal_bank"]
        cls.rule = cls.env["account.reconcile.model"].create(
            {
                "name": "VE Ref Test",
                "sequence": 0,
                "rule_type": "invoice_matching",
                "auto_reconcile": True,
                "match_partner": False,
                "match_nature": "both",
                "match_same_currency": True,
                "allow_payment_tolerance": True,
                "payment_tolerance_type": "percentage",
                "payment_tolerance_param": 0.0,
                "match_text_location_label": False,
                "match_text_location_reference": True,
                "match_text_location_note": False,
                "match_ref_suffix_enabled": True,
                "match_ref_suffix_lengths": "6,4",
                "match_payment_before_invoice": True,
                "company_id": cls.company.id,
            }
        )

    def _create_invoice_line(self, amount, reference):
        invoice = self.init_invoice(
            "out_invoice",
            partner=self.partner_a,
            invoice_date="2026-03-01",
            amounts=[amount],
            post=True,
        )
        invoice.write({"payment_reference": reference, "ref": reference})
        return invoice.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
        )

    def _create_payment_line(self, amount, reference, journal=None):
        payment = self.env["account.payment"].create(
            {
                "amount": amount,
                "date": "2026-03-01",
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.partner_a.id,
                "memo": reference,
                "journal_id": (journal or self.bank_journal).id,
            }
        )
        payment.action_post()
        return payment.move_id.line_ids.filtered(
            lambda line: line.account_id == payment.outstanding_account_id
        )

    def _create_st_line(self, amount, ref, payment_ref="PMPC pago"):
        return self.env["account.bank.statement.line"].create(
            {
                "journal_id": self.bank_journal.id,
                "amount": amount,
                "date": "2026-03-10",
                "payment_ref": payment_ref,
                "ref": ref,
            }
        )

    def _get_candidates(self, st_line):
        return self.rule._get_ref_suffix_amls_candidates(
            st_line, st_line._retrieve_partner()
        )

    def test_exact_payment_match_auto(self):
        payment_line = self._create_payment_line(1000.0, "78131243")
        st_line = self._create_st_line(1000.0, "78131243")
        result = self._get_candidates(st_line)
        self.assertTrue(result["allow_auto_reconcile"])
        self.assertEqual(result["amls"], payment_line)

        applied = self.rule._apply_rules(st_line, st_line._retrieve_partner())
        self.assertEqual(applied.get("model"), self.rule)
        self.assertEqual(applied.get("amls"), payment_line)
        self.assertTrue(applied.get("auto_reconcile"))

    def test_leading_zeros_are_ignored(self):
        payment_line = self._create_payment_line(300.0, "001093594843")
        st_line = self._create_st_line(300.0, "1093594843")
        result = self._get_candidates(st_line)
        self.assertTrue(result["allow_auto_reconcile"])
        self.assertEqual(result["amls"], payment_line)

    def test_invoice_suffix_six_auto(self):
        invoice_line = self._create_invoice_line(500.0, "513367")
        st_line = self._create_st_line(500.0, "000084732513367")
        result = self._get_candidates(st_line)
        self.assertTrue(result["allow_auto_reconcile"])
        self.assertEqual(result["amls"], invoice_line)

    def test_ambiguous_suffix_four_only_suggests(self):
        line_a = self._create_invoice_line(100.0, "11112222")
        line_b = self._create_invoice_line(100.0, "99992222")
        st_line = self._create_st_line(100.0, "55552222")
        result = self._get_candidates(st_line)
        self.assertFalse(result["allow_auto_reconcile"])
        self.assertEqual(result["amls"], line_a | line_b)

    def test_amount_mismatch_only_suggests(self):
        payment_line = self._create_payment_line(150.0, "44556677")
        st_line = self._create_st_line(140.0, "44556677")
        result = self._get_candidates(st_line)
        self.assertFalse(result["allow_auto_reconcile"])
        self.assertEqual(result["amls"], payment_line)

    def test_payment_has_priority_over_invoice(self):
        payment_line = self._create_payment_line(250.0, "3604277894")
        self._create_invoice_line(250.0, "3604277894")
        st_line = self._create_st_line(250.0, "3604277894")
        result = self._get_candidates(st_line)
        self.assertEqual(result["amls"], payment_line)

    def test_free_text_digits_are_not_glued(self):
        self._create_payment_line(80.0, "25992698")
        self.rule.match_text_location_label = True
        st_line = self._create_st_line(
            80.0,
            False,
            payment_ref="TELF.:584245910052 BANCO:0102 CED.:V25992698 PMPC pago",
        )
        self.assertEqual(
            self.rule._get_st_line_ref_candidates(st_line),
            ["584245910052", "0102", "25992698"],
        )

    def test_label_concept_matches_vendor_payment(self):
        payment = self.env["account.payment"].create(
            {
                "amount": 381600.0,
                "date": "2026-03-01",
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": self.partner_a.id,
                "memo": "000052",
                "journal_id": self.bank_journal.id,
            }
        )
        payment.action_post()
        payment_line = payment.move_id.line_ids.filtered(
            lambda line: line.account_id == payment.outstanding_account_id
        )
        self.rule.match_text_location_label = True
        st_line = self._create_st_line(
            -381600.0,
            "621674",
            payment_ref="TELF.:000000000000 CED.:J413176734 "
            "CTA.:01050238151238087019 PRODCON 000052",
        )
        result = self._get_candidates(st_line)
        self.assertTrue(result["allow_auto_reconcile"])
        self.assertEqual(result["amls"], payment_line)

    def test_label_concept_needs_amount_match(self):
        self._create_invoice_line(7377.59, "000181")
        self.rule.match_text_location_label = True
        st_line = self._create_st_line(
            316337.88,
            "181",
            payment_ref="POS: 860978667 FERRE AGRO QUIBOR CA LOTE:000181",
        )
        self.assertFalse(self._get_candidates(st_line))

    def test_short_suffix_is_not_searched(self):
        self._create_payment_line(52.0, "52")
        st_line = self._create_st_line(52.0, "1000052")
        self.assertFalse(self._get_candidates(st_line))

    def test_payment_of_other_journal_is_ignored(self):
        other_journal = self.bank_journal.copy({"name": "Other bank", "code": "OBNK"})
        self._create_payment_line(700.0, "52364178", journal=other_journal)
        st_line = self._create_st_line(700.0, "52364178")
        self.assertFalse(self._get_candidates(st_line))

    def test_suffix_ignores_free_text_references(self):
        self._create_payment_line(90.0, "ENT/2026/06470")
        st_line = self._create_st_line(90.0, "1044076470")
        self.assertFalse(self._get_candidates(st_line))

    def test_ref_only_skips_standard_matching(self):
        self._create_payment_line(6839.0, "0")
        st_line = self._create_st_line(6839.0, "0", payment_ref="Comision")
        partner = st_line._retrieve_partner()
        self.assertEqual(self.rule._apply_rules(st_line, partner).get("model"), self.rule)

        self.rule.match_ref_only = True
        self.assertEqual(list(self.rule._get_invoice_matching_rules_map()), [5])
        self.assertFalse(self.rule._apply_rules(st_line, partner))

    def test_unreliable_ref_is_ignored(self):
        self._create_invoice_line(8.0, "0")
        st_line = self._create_st_line(8.0, "0")
        self.assertFalse(self._get_candidates(st_line))

    def test_no_match_returns_none(self):
        self._create_payment_line(80.0, "11111111")
        st_line = self._create_st_line(80.0, "99999999")
        self.assertFalse(self._get_candidates(st_line))

    def test_imported_lines_are_auto_reconciled(self):
        payment_line = self._create_payment_line(1200.0, "62449235685")
        st_line = self._create_st_line(1200.0, "62449235685")
        st_line._try_auto_reconcile_imported_lines()
        self.assertTrue(st_line.is_reconciled)
        self.assertTrue(payment_line.reconciled)
