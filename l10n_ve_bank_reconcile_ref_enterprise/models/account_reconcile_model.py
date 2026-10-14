# Copyright 2026 andyengit
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import re

from odoo import fields, models
from odoo.osv import expression

MIN_REF_LENGTH = 4
REF_ONLY_RE = re.compile(r"^[\s\-/#.]*\d[\d\s\-/#.]*$")
REF_TOKEN_RE = re.compile(r"\d{4,}")
INVOICE_MOVE_TYPES = (
    "out_invoice",
    "out_refund",
    "out_receipt",
    "in_invoice",
    "in_refund",
    "in_receipt",
)
REF_FIELDS = {
    "payment": ["payment_id.memo", "payment_id.payment_reference", "move_id.ref"],
    "invoice": ["move_id.payment_reference", "move_id.ref"],
}


class AccountReconcileModel(models.Model):
    _inherit = "account.reconcile.model"

    match_ref_suffix_enabled = fields.Boolean(
        string="Match by bank reference",
        help="Match the bank reference of the statement line with the reference "
        "of open payments and invoices: first the full reference, then its "
        "last digits.",
    )
    match_ref_only = fields.Boolean(
        string="Only match by bank reference",
        help="Skip the standard matching (amounts and text tokens) on this "
        "rule, so a line without a reliable bank reference is left for "
        "the next rules or for manual reconciliation.",
    )
    match_ref_suffix_lengths = fields.Char(
        string="Suffix lengths",
        default="6,4",
        help="Comma-separated suffix lengths to try in order, for example: 6,4",
    )
    match_payment_before_invoice = fields.Boolean(
        string="Match payments before invoices",
        default=True,
        help="Search open payments first, then open invoices/bills.",
    )

    def _get_invoice_matching_rules_map(self):
        rules_map = super()._get_invoice_matching_rules_map()
        if self.match_ref_suffix_enabled and self.match_ref_only:
            rules_map.clear()
        rules_map[5].append(self._get_ref_suffix_amls_candidates)
        return rules_map

    def _get_ref_suffix_lengths(self):
        self.ensure_one()
        lengths = []
        for part in (self.match_ref_suffix_lengths or "").split(","):
            part = part.strip()
            if not part.isdigit():
                continue
            length = int(part)
            if length >= MIN_REF_LENGTH and length not in lengths:
                lengths.append(length)
        return lengths or [6, 4]

    def _normalize_ref_digits(self, value):
        raw = re.sub(r"\D", "", value or "")
        digits = raw.lstrip("0")
        if len(digits) >= MIN_REF_LENGTH:
            return digits
        if digits and len(raw) >= MIN_REF_LENGTH:
            return raw
        return ""

    def _extract_ref_digits(self, values, with_tokens=True):
        refs = []
        for value in values:
            if not value:
                continue
            if REF_ONLY_RE.match(value):
                chunks = [value]
            elif with_tokens:
                chunks = REF_TOKEN_RE.findall(value)
            else:
                continue
            for chunk in chunks:
                digits = self._normalize_ref_digits(chunk)
                if digits and digits not in refs:
                    refs.append(digits)
        return refs

    def _get_st_line_ref_candidates(self, st_line, with_tokens=True):
        self.ensure_one()
        return self._extract_ref_digits(
            self._get_st_line_text_values_for_matching(st_line),
            with_tokens=with_tokens,
        )

    def _aml_reference_digits(self, aml, source, with_tokens=True):
        if source == "payment":
            values = [
                aml.payment_id.memo,
                aml.payment_id.payment_reference,
                aml.move_id.ref,
            ]
        else:
            values = [aml.move_id.payment_reference, aml.move_id.ref]
        return self._extract_ref_digits(values, with_tokens=with_tokens)

    def _ref_matches(self, st_ref, aml_refs, mode, suffix_len=None):
        if mode == "exact":
            return st_ref in aml_refs
        if not suffix_len or len(st_ref) < suffix_len:
            return False
        st_suffix = st_ref[-suffix_len:]
        st_suffix_digits = st_suffix.lstrip("0")
        for aml_ref in aml_refs:
            if aml_ref == st_suffix_digits:
                return True
            if len(aml_ref) >= suffix_len and aml_ref[-suffix_len:] == st_suffix:
                return True
        return False

    def _get_ref_match_amls_domain(self, st_line, partner, source):
        domain = self._get_invoice_matching_amls_domain(st_line, partner)
        if source == "payment":
            domain.append(("payment_id.journal_id", "=", st_line.journal_id.id))
        else:
            domain.extend(
                [
                    ("payment_id", "=", False),
                    ("move_id.move_type", "in", INVOICE_MOVE_TYPES),
                ]
            )
        return domain

    def _get_ref_match_text_domains(self, source, st_refs, mode, suffix_len):
        patterns = []
        for st_ref in st_refs:
            if mode == "exact":
                patterns.append(st_ref)
            elif suffix_len and len(st_ref) >= suffix_len:
                patterns.append(st_ref[-suffix_len:].lstrip("0"))
        patterns = [
            pattern
            for pattern in dict.fromkeys(patterns)
            if len(pattern) >= MIN_REF_LENGTH
        ]
        return [
            [(field_name, "=like", f"%{pattern}")]
            for pattern in patterns
            for field_name in REF_FIELDS[source]
        ]

    def _amount_matches_st_line(self, st_line, aml):
        st_line_currency = st_line.foreign_currency_id or st_line.currency_id
        st_line_amount = st_line._prepare_move_line_default_vals()[1]["amount_currency"]
        counterpart = st_line._prepare_counterpart_amounts_using_st_line_rate(
            aml.currency_id,
            aml.amount_residual,
            aml.amount_residual_currency,
        )
        residual = st_line_currency.round(
            st_line_amount + counterpart["amount_currency"]
        )
        if st_line_currency.is_zero(residual):
            return True
        if not self.allow_payment_tolerance or not self.payment_tolerance_param:
            return False
        if self.payment_tolerance_type == "percentage":
            max_gap = abs(st_line_amount) * (self.payment_tolerance_param / 100.0)
        else:
            max_gap = self.payment_tolerance_param
        return abs(residual) <= st_line_currency.round(max_gap)

    def _search_ref_match_amls(
        self, st_line, partner, source, st_refs, mode, suffix_len
    ):
        aml_model = self.env["account.move.line"]
        text_domains = self._get_ref_match_text_domains(
            source, st_refs, mode, suffix_len
        )
        if not text_domains:
            return aml_model
        domain = expression.AND(
            [
                self._get_ref_match_amls_domain(st_line, partner, source),
                expression.OR(text_domains),
            ]
        )
        with_tokens = mode == "exact"
        return aml_model.search(domain, limit=200).filtered(
            lambda aml: any(
                self._ref_matches(
                    st_ref,
                    self._aml_reference_digits(aml, source, with_tokens=with_tokens),
                    mode,
                    suffix_len=suffix_len,
                )
                for st_ref in st_refs
            )
        )

    def _build_ref_match_result(self, st_line, amls, require_amount=False):
        if not amls:
            return None
        amount_matched = amls.filtered(
            lambda aml: self._amount_matches_st_line(st_line, aml)
        )
        if require_amount and not amount_matched:
            return None
        return {
            "allow_auto_reconcile": len(amount_matched) == 1,
            "amls": amount_matched or amls,
        }

    def _get_ref_match_passes(self, st_line):
        whole_refs = self._get_st_line_ref_candidates(st_line, with_tokens=False)
        token_refs = [
            ref
            for ref in self._get_st_line_ref_candidates(st_line)
            if ref not in whole_refs
        ]
        return [
            ("exact", None, whole_refs, False),
            ("exact", None, token_refs, True),
        ] + [
            ("suffix", length, whole_refs, False)
            for length in self._get_ref_suffix_lengths()
        ]

    def _get_ref_suffix_amls_candidates(self, st_line, partner):
        self.ensure_one()
        if self.rule_type != "invoice_matching" or not self.match_ref_suffix_enabled:
            return None

        sources = (
            ("payment", "invoice")
            if self.match_payment_before_invoice
            else ("invoice", "payment")
        )
        for mode, suffix_len, st_refs, require_amount in self._get_ref_match_passes(
            st_line
        ):
            if not st_refs:
                continue
            for source in sources:
                amls = self._search_ref_match_amls(
                    st_line, partner, source, st_refs, mode, suffix_len
                )
                result = self._build_ref_match_result(
                    st_line, amls, require_amount=require_amount
                )
                if result:
                    return result
        return None
