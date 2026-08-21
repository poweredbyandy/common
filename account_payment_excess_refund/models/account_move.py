from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import formatLang


class AccountMove(models.Model):
    _inherit = "account.move"

    excess_refund_payment_ids = fields.One2many(
        comodel_name="account.payment",
        inverse_name="excess_refund_invoice_id",
        string="Excess Refund Payments",
    )
    has_excess_to_refund = fields.Boolean(
        compute="_compute_excess_to_refund",
    )
    has_excess_refunded = fields.Boolean(
        compute="_compute_excess_to_refund",
    )
    show_excess_refund_section = fields.Boolean(
        compute="_compute_excess_to_refund",
    )
    excess_to_refund_amount = fields.Monetary(
        string="Excess to Refund",
        currency_field="currency_id",
        compute="_compute_excess_to_refund",
    )
    excess_refunded_amount = fields.Monetary(
        string="Excess Refunded",
        currency_field="currency_id",
        compute="_compute_excess_to_refund",
    )
    excess_refund_payment_count = fields.Integer(
        compute="_compute_excess_to_refund",
    )
    excess_refund_payments_widget = fields.Binary(
        compute="_compute_excess_to_refund",
        exportable=False,
    )
    excess_to_refund_widget = fields.Binary(
        compute="_compute_excess_to_refund",
        exportable=False,
    )

    def _excess_refund_partner_type(self):
        self.ensure_one()
        if self.is_sale_document(include_receipts=True):
            return "customer"
        if self.is_purchase_document(include_receipts=True):
            return "supplier"
        return False

    def _get_excess_refund_source_payments(self):
        self.ensure_one()
        return self.reconciled_payment_ids | self.matched_payment_ids

    def _is_excess_refund_liquidity_line(self, line, payment):
        if not payment:
            return False
        return line.account_id in payment._get_valid_liquidity_accounts()

    def _line_has_excess_residual(self, line):
        if line.currency_id and not line.currency_id.is_zero(
            line.amount_residual_currency
        ):
            return True
        return not line.company_currency_id.is_zero(line.amount_residual)

    def _is_customer_excess_line(self, line):
        if line.currency_id:
            return line.currency_id.compare_amounts(
                line.amount_residual_currency, 0.0
            ) < 0
        return line.company_currency_id.compare_amounts(line.amount_residual, 0.0) < 0

    def _is_supplier_excess_line(self, line):
        if line.currency_id:
            return line.currency_id.compare_amounts(
                line.amount_residual_currency, 0.0
            ) > 0
        return line.company_currency_id.compare_amounts(line.amount_residual, 0.0) > 0

    def _line_matches_excess_sign(self, line, partner_type):
        if partner_type == "customer":
            return self._is_customer_excess_line(line)
        if partner_type == "supplier":
            return self._is_supplier_excess_line(line)
        return False

    def _line_belongs_to_invoice_partner(self, line):
        self.ensure_one()
        line_partner = line.partner_id or line.move_id.partner_id
        if not line_partner:
            return False
        return (
            line_partner.commercial_partner_id
            == self.commercial_partner_id
        )

    def _is_eligible_excess_refund_line(self, line, partner_type, payment=False):
        self.ensure_one()
        if line.parent_state != "posted":
            return False
        if not line.account_id.reconcile:
            return False
        if line.reconciled:
            return False
        if line.display_type in ("line_section", "line_note"):
            return False
        if line.company_id != self.company_id:
            return False
        if not self._line_has_excess_residual(line):
            return False
        if self._is_excess_refund_liquidity_line(line, payment):
            return False
        if not self._line_belongs_to_invoice_partner(line):
            return False
        return self._line_matches_excess_sign(line, partner_type)

    def _get_excess_line_amount_in_currency(self, line, currency):
        self.ensure_one()
        if currency == line.company_currency_id:
            return abs(line.amount_residual)
        if line.currency_id == currency:
            return abs(line.amount_residual_currency)
        if line.company_currency_id.is_zero(line.amount_residual):
            return 0.0
        return line.company_currency_id._convert(
            abs(line.amount_residual),
            currency,
            self.company_id,
            line.date or self.date or fields.Date.context_today(self),
        )

    def _get_excess_refund_lines(self):
        self.ensure_one()
        partner_type = self._excess_refund_partner_type()
        if not partner_type or self.state != "posted":
            return self.env["account.move.line"]
        payments = self._get_excess_refund_source_payments().filtered(
            lambda payment: payment.state in ("paid", "in_process")
            and payment.move_id
        )
        excess_lines = self.env["account.move.line"]
        for payment in payments:
            for line in payment.move_id.line_ids:
                if self._is_eligible_excess_refund_line(line, partner_type, payment):
                    excess_lines |= line
        return excess_lines

    def _get_excess_refund_payments(self, include_canceled=False):
        self.ensure_one()
        payments = self.excess_refund_payment_ids
        if include_canceled:
            return payments
        return payments.filtered(lambda payment: payment.state in ("paid", "in_process"))

    def _get_excess_source_payments(self):
        self.ensure_one()
        payments = self.env["account.payment"]
        refunds = self.excess_refund_payment_ids
        payments |= refunds.mapped("excess_refund_source_payment_id")
        for line in self._get_excess_refund_lines():
            payments |= line.payment_id or line.move_id.origin_payment_id
        return payments

    def _get_payment_amount_in_currency(self, payment, currency):
        self.ensure_one()
        if payment.currency_id == currency:
            return payment.amount
        company_amount = abs(payment.amount_company_currency_signed)
        if currency == payment.company_currency_id:
            return company_amount
        return payment.company_currency_id._convert(
            company_amount,
            currency,
            payment.company_id,
            payment.date or fields.Date.context_today(self),
        )

    def _prepare_excess_refund_payments_widget(self, refund_payments):
        self.ensure_one()
        content = []
        for payment in refund_payments.sorted(key=lambda item: (item.date, item.id)):
            amount = self._get_payment_amount_in_currency(payment, self.currency_id)
            if self.currency_id.is_zero(amount):
                continue
            foreign_currency = False
            if (
                payment.currency_id
                and payment.currency_id != payment.company_currency_id
                and payment.currency_id != self.currency_id
            ):
                foreign_currency = payment.currency_id
            content.append(
                {
                    "name": payment.name,
                    "journal_name": payment.journal_id.name,
                    "amount": amount,
                    "currency_id": self.currency_id.id,
                    "date": fields.Date.to_string(payment.date),
                    "account_payment_id": payment.id,
                    "payment_method_name": payment.payment_method_line_id.name,
                    "move_id": payment.move_id.id,
                    "ref": payment.memo or payment.name,
                    "amount_company_currency": formatLang(
                        self.env,
                        abs(payment.amount_company_currency_signed),
                        currency_obj=payment.company_currency_id,
                    ),
                    "amount_foreign_currency": foreign_currency
                    and formatLang(
                        self.env,
                        payment.amount,
                        currency_obj=foreign_currency,
                    ),
                    "can_cancel": payment.state in ("paid", "in_process", "draft"),
                }
            )
        if not content:
            return False
        return {
            "title": _("Excess Refunded"),
            "outstanding": False,
            "content": content,
            "move_id": self.id,
        }

    def _prepare_excess_to_refund_widget(self, excess_lines):
        self.ensure_one()
        content = []
        for line in excess_lines.sorted(key=lambda item: (item.date, item.id)):
            amount = self._get_excess_line_amount_in_currency(line, self.currency_id)
            if self.currency_id.is_zero(amount):
                continue
            payment = line.payment_id or line.move_id.origin_payment_id
            content.append(
                {
                    "journal_name": payment.display_name
                    if payment
                    else (line.ref or line.move_id.name),
                    "amount": amount,
                    "currency_id": self.currency_id.id,
                    "id": line.id,
                    "move_id": line.move_id.id,
                    "date": fields.Date.to_string(line.date),
                    "account_payment_id": payment.id if payment else False,
                }
            )
        if not content:
            return False
        return {
            "title": _("Excess to Refund"),
            "outstanding": True,
            "content": content,
            "move_id": self.id,
        }

    @api.depends(
        "state",
        "move_type",
        "partner_id",
        "company_id",
        "currency_id",
        "reconciled_payment_ids",
        "matched_payment_ids",
        "reconciled_payment_ids.state",
        "matched_payment_ids.state",
        "reconciled_payment_ids.move_id.line_ids.amount_residual",
        "reconciled_payment_ids.move_id.line_ids.amount_residual_currency",
        "reconciled_payment_ids.move_id.line_ids.reconciled",
        "matched_payment_ids.move_id.line_ids.amount_residual",
        "matched_payment_ids.move_id.line_ids.amount_residual_currency",
        "matched_payment_ids.move_id.line_ids.reconciled",
        "excess_refund_payment_ids",
        "excess_refund_payment_ids.state",
        "excess_refund_payment_ids.amount",
        "excess_refund_payment_ids.currency_id",
        "excess_refund_payment_ids.amount_company_currency_signed",
        "excess_refund_payment_ids.date",
        "excess_refund_payment_ids.journal_id",
        "excess_refund_payment_ids.memo",
        "excess_refund_payment_ids.payment_method_line_id",
    )
    def _compute_excess_to_refund(self):
        for move in self:
            excess_lines = move._get_excess_refund_lines()
            open_amount = 0.0
            for line in excess_lines:
                open_amount += move._get_excess_line_amount_in_currency(
                    line, move.currency_id
                )
            refund_payments = move._get_excess_refund_payments()
            refunded_amount = 0.0
            for payment in refund_payments:
                refunded_amount += move._get_payment_amount_in_currency(
                    payment, move.currency_id
                )
            move.excess_to_refund_amount = open_amount
            move.excess_refunded_amount = refunded_amount
            move.has_excess_to_refund = bool(excess_lines) and not move.currency_id.is_zero(
                open_amount
            )
            move.has_excess_refunded = not move.currency_id.is_zero(refunded_amount)
            move.excess_refund_payment_count = len(refund_payments)
            move.show_excess_refund_section = (
                move.has_excess_to_refund or move.has_excess_refunded
            )
            move.excess_refund_payments_widget = (
                move._prepare_excess_refund_payments_widget(refund_payments)
                if move.has_excess_refunded
                else False
            )
            move.excess_to_refund_widget = (
                move._prepare_excess_to_refund_widget(excess_lines)
                if move.has_excess_to_refund
                else False
            )

    def _prepare_excess_refund_register_context(self, excess_lines):
        self.ensure_one()
        partner_type = self._excess_refund_partner_type()
        source_payments = excess_lines.mapped("payment_id") | excess_lines.mapped(
            "move_id.origin_payment_id"
        )
        context = {
            "active_model": "account.move.line",
            "active_ids": excess_lines.ids,
            "active_id": excess_lines[:1].id,
            "dont_redirect_to_payments": True,
            "display_account_trust": True,
            "account_payment_excess_refund": True,
            "excess_refund_invoice_id": self.id,
            "excess_refund_partner_type": partner_type,
            "excess_refund_account_types": list(
                set(excess_lines.mapped("account_type"))
            ),
            "excess_refund_source_payment_ids": source_payments.ids,
            "default_group_payment": True,
            "default_communication": _(
                "Excess refund: %(invoice)s",
                invoice=self.display_name,
            ),
        }
        journal = self.company_id.excess_refund_journal_id
        if journal:
            context["default_journal_id"] = journal.id
        return context

    def _action_open_excess_refund_register(self, excess_lines):
        self.ensure_one()
        return {
            "name": _("Return Excess"),
            "type": "ir.actions.act_window",
            "res_model": "account.payment.register",
            "view_mode": "form",
            "views": [[False, "form"]],
            "target": "new",
            "context": self._prepare_excess_refund_register_context(excess_lines),
        }

    def _action_open_excess_refund_lines(self, excess_lines):
        self.ensure_one()
        return {
            "name": _("Excess to Refund"),
            "type": "ir.actions.act_window",
            "res_model": "account.move.line",
            "view_mode": "list",
            "views": [
                (
                    self.env.ref(
                        "account_payment_excess_refund.view_move_line_excess_refund_list"
                    ).id,
                    "list",
                )
            ],
            "domain": [("id", "in", excess_lines.ids)],
            "target": "current",
            "context": {
                "create": False,
                "edit": False,
                "excess_refund_invoice_id": self.id,
                "excess_refund_partner_type": self._excess_refund_partner_type(),
                "account_payment_excess_refund": True,
            },
        }

    def action_return_excess(self):
        self.ensure_one()
        if self.state != "posted":
            raise UserError(_("You can only refund excesses on posted invoices."))
        if not self._excess_refund_partner_type():
            raise UserError(
                _("Excess refunds are only available on customer or vendor invoices.")
            )
        excess_lines = self._get_excess_refund_lines()
        if not excess_lines:
            raise UserError(_("There is no open payment excess to refund on this invoice."))
        if len(excess_lines) == 1:
            return self._action_open_excess_refund_register(excess_lines)
        return self._action_open_excess_refund_lines(excess_lines)

    def js_action_return_excess_line(self, line_id):
        self.ensure_one()
        if self.state != "posted":
            raise UserError(_("You can only refund excesses on posted invoices."))
        line = self.env["account.move.line"].browse(line_id).exists()
        if not line or line not in self._get_excess_refund_lines():
            raise UserError(_("There is no open payment excess to refund on this invoice."))
        return self._action_open_excess_refund_register(line)

    def js_action_cancel_excess_refund_payment(self, payment_id):
        self.ensure_one()
        payment = self.env["account.payment"].browse(payment_id).exists()
        if not payment or payment.excess_refund_invoice_id != self:
            raise UserError(_("There is no excess refund payment to cancel."))
        payment._excess_refund_cancel_payments()
        return True

    def js_action_open_excess_refund_payment(self, payment_id):
        self.ensure_one()
        payment = self.env["account.payment"].browse(payment_id).exists()
        if not payment or payment.excess_refund_invoice_id != self:
            raise UserError(_("There is no excess refund payment on this invoice."))
        return {
            "name": payment.display_name,
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "res_id": payment.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }

    def action_view_excess_refund_payments(self):
        self.ensure_one()
        payments = self._get_excess_refund_payments(include_canceled=True)
        if not payments:
            raise UserError(_("There is no excess refund payment on this invoice."))
        list_view = self.env.ref(
            "account_payment_excess_refund.view_account_payment_excess_refund_list"
        )
        return {
            "name": _("Excess Refunds"),
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "view_mode": "list,form",
            "views": [
                (list_view.id, "list"),
                (False, "form"),
            ],
            "domain": [("id", "in", payments.ids)],
            "context": {
                "create": False,
                "excess_refund_invoice_id": self.id,
            },
        }

    def action_cancel_excess_refund_payments(self):
        self.ensure_one()
        refunds = self._get_excess_refund_payments()
        if not refunds:
            raise UserError(_("There is no excess refund payment to cancel."))
        refunds._excess_refund_cancel_payments()
        return True

