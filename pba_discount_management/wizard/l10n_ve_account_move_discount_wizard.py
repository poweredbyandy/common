from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class L10nVeAccountMoveDiscountWizard(models.TransientModel):
    _inherit = "l10n.ve.account.move.discount.wizard"

    def action_apply_discount(self):
        self.ensure_one()
        policy = self.env["pba.discount.policy"]
        policy._pba_require_global_discount_rights()
        move = self.move_id
        if move.pba_discount_legacy:
            raise UserError(
                _(
                    "This invoice uses legacy product discount lines. "
                    "Use the Discount button to manage them."
                )
            )
        if self.discount_mode == "percentage":
            policy._pba_raise_if_ratio_over_limit(
                self.discount_percentage, move.company_id, move.partner_id
            )
        else:
            subtotal_by_taxes = move._l10n_ve_global_discount_subtotal_by_taxes()
            total_subtotal = sum(subtotal_by_taxes.values())
            already_applied = move._l10n_ve_total_sequential_global_discount(
                subtotal_by_taxes
            )
            remaining = total_subtotal - already_applied
            ratio = (self.amount / remaining) if remaining else 0.0
            if float_compare(ratio, 0.0, precision_digits=6) > 0:
                policy._pba_raise_if_ratio_over_limit(
                    ratio, move.company_id, move.partner_id
                )
        return super().action_apply_discount()
