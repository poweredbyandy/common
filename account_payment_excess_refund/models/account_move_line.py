from odoo import _, models
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def action_return_excess(self):
        invoice = self.env["account.move"].browse(
            self.env.context.get("excess_refund_invoice_id")
        )
        if not invoice:
            raise UserError(_("Open the excess refund from the related invoice."))
        if not self:
            raise UserError(_("Select at least one excess line to refund."))
        eligible = invoice._get_excess_refund_lines() & self
        if not eligible or set(self.ids) - set(eligible.ids):
            raise UserError(
                _("One or more selected lines are not an open excess of this invoice.")
            )
        return invoice._action_open_excess_refund_register(self)
