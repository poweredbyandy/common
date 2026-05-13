from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class SaleOrder(models.Model):
    _inherit = "sale.order"

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
        "payment_term_id",
        "payment_term_id.line_ids.nb_days",
        "payment_term_id.line_ids.delay_type",
    )
    def _compute_is_credit_sale(self):
        for order in self:
            order.is_credit_sale = bool(
                order.payment_term_id
                and order.payment_term_id._is_credit_sale_authorization_term()
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

    @api.depends("partner_id", "company_id")
    def _compute_payment_term_id(self):
        res = super()._compute_payment_term_id()
        for order in self:
            if order._is_credit_authorized_by_partner():
                order.credit_authorized = True
        return res

    @api.onchange("partner_id", "payment_term_id")
    def _onchange_credit_authorized_from_partner(self):
        for order in self:
            if order._is_credit_authorized_by_partner():
                order.credit_authorized = True

    def write(self, vals):
        if "credit_authorized" in vals and not self.env.user.has_group(
            "credit_sale_authorization.group_credit_sale_confirm"
        ):
            if vals["credit_authorized"] and all(
                order._is_credit_authorized_by_partner() for order in self
            ):
                return super().write(vals)
            raise AccessError(
                _(
                    "No tiene permiso para modificar el campo 'Crédito Autorizado'. "
                    "Contacte a un usuario autorizado para ventas a crédito."
                )
            )
        return super().write(vals)

    def _confirmation_error_message(self):
        error = super()._confirmation_error_message()
        if error:
            return error
        if (
            self.is_credit_sale
            and not self.credit_authorized
            and not self._is_credit_authorized_by_partner()
        ):
            return _(
                "No se puede confirmar el presupuesto '%(order)s' porque es una "
                "venta a crédito y no ha sido autorizada. Solicite la autorización "
                "a un usuario autorizado para ventas a crédito.",
                order=self.name,
            )
        return False

    def _prepare_invoice(self):
        values = super()._prepare_invoice()
        if self.credit_authorized or self._is_credit_authorized_by_partner():
            values["credit_authorized"] = True
        return values
