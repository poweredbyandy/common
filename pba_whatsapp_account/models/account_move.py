from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "mail.whatsapp.mixin"]

    whatsapp_phone = fields.Char(compute="_compute_whatsapp_phone")

    @api.depends("partner_id", "partner_id.mobile", "partner_id.phone")
    def _compute_whatsapp_phone(self):
        for move in self:
            move.whatsapp_phone = (
                move.partner_id.mobile or move.partner_id.phone or ""
            )

    def _whatsapp_get_partner(self):
        return self.partner_id

    def _whatsapp_get_channel(self, field_name, gateway):
        self.ensure_one()
        partner = self.partner_id
        if not partner:
            raise UserError(_("La factura no tiene un cliente asociado."))
        phone_field = "mobile" if partner.mobile else "phone"
        return partner._whatsapp_get_channel(phone_field, gateway)

    def _get_whatsapp_invoice_body(self):
        self.ensure_one()
        return _(
            "Estimado/a %s, le enviamos su factura %s por %s."
        ) % (
            self.partner_id.name,
            self.name,
            self.currency_id.format(self.amount_total),
        )

    def _get_whatsapp_overdue_body(self):
        self.ensure_one()
        due = self.invoice_date_due or self.invoice_date
        return _(
            "Estimado/a %s, le recordamos que la factura %s por %s "
            "se encuentra vencida desde %s."
        ) % (
            self.partner_id.name,
            self.name,
            self.currency_id.format(self.amount_residual),
            due,
        )

    def action_whatsapp_send_invoice(self):
        self.ensure_one()
        if self.move_type not in ("out_invoice", "out_refund"):
            raise UserError(_("Solo se pueden enviar facturas de cliente."))
        template = self.company_id.whatsapp_template_invoice_id
        body = template.body if template else self._get_whatsapp_invoice_body()
        return self.action_whatsapp_send(body, template=template)

    def action_whatsapp_send_overdue(self):
        self.ensure_one()
        template = self.company_id.whatsapp_template_overdue_id
        body = template.body if template else self._get_whatsapp_overdue_body()
        return self.action_whatsapp_send(body, template=template)

    @api.model
    def _cron_whatsapp_send_overdue_invoices(self):
        for company in self.env["res.company"].search(
            [("whatsapp_overdue_auto_send", "=", True)]
        ):
            min_due = fields.Date.today() - timedelta(
                days=company.whatsapp_overdue_days
            )
            moves = self.search(
                [
                    ("company_id", "=", company.id),
                    ("move_type", "=", "out_invoice"),
                    ("state", "=", "posted"),
                    ("payment_state", "in", ("not_paid", "partial")),
                    ("invoice_date_due", "<=", min_due),
                ]
            )
            for move in moves:
                if not move.partner_id or not (
                    move.partner_id.mobile or move.partner_id.phone
                ):
                    continue
                body = (
                    company.whatsapp_template_overdue_id.body
                    if company.whatsapp_template_overdue_id
                    else move._get_whatsapp_overdue_body()
                )
                template = company.whatsapp_template_overdue_id
                try:
                    gateway = move._whatsapp_get_gateway()
                    channel = move._whatsapp_get_channel("whatsapp_phone", gateway)
                    channel.with_context(
                        whatsapp_template_id=template.id if template else False
                    ).message_post(
                        body=body,
                        subtype_xmlid="mail.mt_comment",
                        message_type="comment",
                    )
                except UserError:
                    continue
