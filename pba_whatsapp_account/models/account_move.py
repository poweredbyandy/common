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

    def action_whatsapp_send_overdue(self):
        self.ensure_one()
        template = self.company_id.whatsapp_template_overdue_id
        body, template, variables = self._pba_whatsapp_prepare_send(
            template, self._get_whatsapp_overdue_body()
        )
        return self.action_whatsapp_send(
            body, template=template, template_variables=variables
        )

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
                template = company.whatsapp_template_overdue_id
                if template:
                    body, variables = template._pba_prepare_body_and_variables(move)
                else:
                    body = move._get_whatsapp_overdue_body()
                    variables = None
                try:
                    gateway = move._whatsapp_get_gateway()
                    channel = move._whatsapp_get_channel("whatsapp_phone", gateway)
                    ctx = {
                        "pba_whatsapp_res_model": move._name,
                        "pba_whatsapp_res_id": move.id,
                    }
                    if template:
                        ctx["whatsapp_template_id"] = template.id
                    if variables is not None:
                        ctx["whatsapp_template_variables"] = variables
                    channel.with_context(**ctx).message_post(
                        body=body,
                        subtype_xmlid="mail.mt_comment",
                        message_type="comment",
                    )
                except UserError:
                    continue
