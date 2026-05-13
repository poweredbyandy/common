from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class ResPartner(models.Model):
    _inherit = "res.partner"

    credit_authorized = fields.Boolean(
        string="Crédito Autorizado",
        compute="_compute_credit_authorized",
        inverse="_inverse_credit_authorized",
        store=True,
        readonly=False,
        tracking=True,
    )
    credit_authorized_manual = fields.Boolean(
        string="Crédito Autorizado Manual",
    )
    can_authorize_credit = fields.Boolean(
        compute="_compute_can_authorize_credit",
    )

    @api.depends(
        "credit_authorized_manual",
        "property_payment_term_id",
        "property_payment_term_id.line_ids.nb_days",
        "property_payment_term_id.line_ids.delay_type",
    )
    def _compute_credit_authorized(self):
        for partner in self:
            payment_term = partner.property_payment_term_id
            partner.credit_authorized = (
                partner.credit_authorized_manual
                or bool(
                    payment_term
                    and payment_term._is_credit_sale_authorization_term()
                )
            )

    def _inverse_credit_authorized(self):
        for partner in self:
            partner.credit_authorized_manual = partner.credit_authorized

    def _compute_can_authorize_credit(self):
        can = self.env.user.has_group(
            "credit_sale_authorization.group_credit_sale_confirm"
        )
        for record in self:
            record.can_authorize_credit = can

    def _is_credit_sale_authorized(self):
        self.ensure_one()
        return self.commercial_partner_id.credit_authorized

    def write(self, vals):
        if (
            {"credit_authorized", "credit_authorized_manual"} & set(vals)
            and not self.env.user.has_group(
                "credit_sale_authorization.group_credit_sale_confirm"
            )
        ):
            raise AccessError(
                _(
                    "No tiene permiso para modificar el campo 'Crédito Autorizado'. "
                    "Contacte a un usuario autorizado para ventas a crédito."
                )
            )
        return super().write(vals)
