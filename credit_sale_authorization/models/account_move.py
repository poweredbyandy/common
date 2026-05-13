from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    is_credit_sale = fields.Boolean(
        string="Es venta a crédito",
        compute="_compute_is_credit_sale",
        store=True,
    )
    credit_authorized = fields.Boolean(
        string="Crédito Autorizado",
        default=False,
        tracking=True,
    )
    can_authorize_credit = fields.Boolean(
        compute="_compute_can_authorize_credit",
    )

    @api.depends(
        "invoice_payment_term_id",
        "invoice_payment_term_id.line_ids.nb_days",
        "invoice_payment_term_id.line_ids.delay_type",
    )
    def _compute_is_credit_sale(self):
        for move in self:
            move.is_credit_sale = bool(
                move.invoice_payment_term_id
                and move.invoice_payment_term_id._is_credit_sale_authorization_term()
            )

    def _compute_can_authorize_credit(self):
        can = self.env.user.has_group(
            "credit_sale_authorization.group_credit_sale_confirm"
        )
        for record in self:
            record.can_authorize_credit = can

    def _is_credit_authorized_by_partner(self):
        self.ensure_one()
        return bool(
            self.partner_id and self.partner_id._is_credit_sale_authorized()
        )

    @api.depends("partner_id")
    def _compute_invoice_payment_term_id(self):
        res = super()._compute_invoice_payment_term_id()
        for move in self:
            if move._is_credit_authorized_by_partner():
                move.credit_authorized = True
        return res

    @api.onchange("partner_id", "invoice_payment_term_id")
    def _onchange_credit_authorized_from_partner(self):
        for move in self:
            if move._is_credit_authorized_by_partner():
                move.credit_authorized = True

    def write(self, vals):
        if "credit_authorized" in vals and not self.env.user.has_group(
            "credit_sale_authorization.group_credit_sale_confirm"
        ):
            if vals["credit_authorized"] and all(
                move._is_credit_authorized_by_partner() for move in self
            ):
                return super().write(vals)
            raise AccessError(
                _(
                    "No tiene permiso para modificar el campo 'Crédito Autorizado'. "
                    "Contacte a un usuario autorizado para ventas a crédito."
                )
            )
        return super().write(vals)

    def _post(self, soft=True):
        for move in self:
            if (
                move.is_invoice(include_receipts=True)
                and move.is_credit_sale
                and not move.credit_authorized
                and not move._is_credit_authorized_by_partner()
            ):
                raise UserError(
                    _(
                        "No se puede confirmar la factura '%(move)s' porque es una "
                        "venta a crédito y no ha sido autorizada. Solicite la autorización "
                        "a un usuario autorizado para ventas a crédito.",
                        move=move.name,
                    )
                )
        return super()._post(soft=soft)
