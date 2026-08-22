from odoo import fields, models, _


class AccountMove(models.Model):
    _inherit = "account.move"

    auto_generated = fields.Boolean(
        string="Auto Generated Document",
        copy=False,
        default=False,
    )
    auto_invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="Source Invoice",
        readonly=True,
        copy=False,
        index="btree_not_null",
    )

    def _post(self, soft=True):
        posted = super()._post(soft)
        if self.env.context.get("skip_ic_invoice_sync"):
            return posted
        invoices_map = {}
        for invoice in posted.filtered(lambda move: move.is_sale_document()):
            company = self.env["res.company"].sudo()._find_company_from_partner(invoice.partner_id.id)
            if company and company.ic_invoice_mode != "none" and not invoice.auto_generated:
                invoices_map.setdefault(company, self.env["account.move"])
                invoices_map[company] += invoice
        for company, invoices in invoices_map.items():
            context = dict(self.env.context, default_company_id=company.id)
            context.pop("default_journal_id", None)
            context.pop("default_invoice_payment_term_id", None)
            invoices.with_user(company.ic_user_id).with_company(company).with_context(
                context
            )._ic_create_counterpart_invoices(company)
        return posted

    def _ic_create_counterpart_invoices(self, company):
        inverse_types = {
            "out_invoice": "in_invoice",
            "out_refund": "in_refund",
        }
        moves = self.env["account.move"]
        for invoice in self:
            if invoice.move_type not in inverse_types:
                continue
            invoice_vals = invoice._ic_prepare_invoice_data(inverse_types[invoice.move_type], company)
            invoice_vals["invoice_line_ids"] = []
            for line in invoice.invoice_line_ids:
                invoice_vals["invoice_line_ids"].append(
                    (0, 0, line._ic_prepare_invoice_line_data(company))
                )
            move = (
                self.env["account.move"]
                .with_company(company)
                .with_context(default_move_type=invoice_vals["move_type"])
                .create(invoice_vals)
            )
            for line in move.invoice_line_ids.filtered(
                lambda move_line: move_line.display_type not in ("line_note", "line_section")
            ):
                price_unit = line.price_unit
                line.tax_ids = line._get_computed_taxes()
                line.price_unit = price_unit
            move.message_post(
                body=_(
                    "Automatically generated from %(origin)s of company %(company)s.",
                    origin=invoice.name,
                    company=invoice.company_id.name,
                )
            )
            if company.ic_invoice_mode == "posted":
                move.with_context(skip_ic_invoice_sync=True)._post(soft=True)
            moves += move
        return moves

    def _ic_prepare_invoice_data(self, invoice_type, company):
        self.ensure_one()
        delivery_partner_id = self.company_id.partner_id.address_get(["delivery"])["delivery"]
        delivery_partner = self.env["res.partner"].browse(delivery_partner_id)
        fiscal_position = (
            self.env["account.fiscal.position"]
            .with_company(company)
            ._get_fiscal_position(self.company_id.partner_id, delivery=delivery_partner)
        )
        journal = company.ic_purchase_journal_id
        if not journal:
            journal = self.env["account.journal"].search(
                [("type", "=", "purchase"), ("company_id", "=", company.id)],
                limit=1,
            )
        return {
            "move_type": invoice_type,
            "ref": self.name,
            "partner_id": self.company_id.partner_id.id,
            "currency_id": self.currency_id.id,
            "auto_generated": True,
            "auto_invoice_id": self.id,
            "company_id": company.id,
            "invoice_date": self.invoice_date,
            "invoice_date_due": self.invoice_date_due,
            "payment_reference": self.payment_reference,
            "invoice_origin": _(
                "%(company)s Invoice: %(entry)s",
                company=self.company_id.name,
                entry=self.name,
            ),
            "fiscal_position_id": fiscal_position.id,
            "journal_id": journal.id,
            "invoice_payment_term_id": (
                self.invoice_payment_term_id.id
                if self.invoice_payment_term_id and not self.invoice_payment_term_id.company_id
                else False
            ),
        }


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _ic_prepare_invoice_line_data(self, company):
        self.ensure_one()
        vals = {
            "display_type": self.display_type,
            "sequence": self.sequence,
            "name": self.name,
            "quantity": self.quantity,
            "discount": self.discount,
            "price_unit": self.price_unit,
        }
        if self.product_id.company_id:
            vals["name"] = self.product_id.name
        else:
            vals.update(
                {
                    "product_id": self.product_id.id,
                    "product_uom_id": self.product_uom_id.id,
                }
            )
        return vals
