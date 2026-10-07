from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    treasury_match_ids = fields.One2many(
        "account.treasury.match",
        "payment_id",
        string="Treasury Real Movements",
        groups="account_treasury.group_account_treasury_user",
    )
    treasury_forecast_count = fields.Integer(
        compute="_compute_treasury_forecast_count",
        groups="account_treasury.group_account_treasury_user",
    )

    @api.depends("treasury_match_ids")
    def _compute_treasury_forecast_count(self):
        for payment in self:
            payment.treasury_forecast_count = len(
                payment.treasury_match_ids.forecast_id
            )

    def action_open_treasury_assign(self):
        self.ensure_one()
        if self.state not in ("in_process", "paid"):
            raise UserError(_("Confirm the payment before assigning it to forecasts."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Assign to Forecasts"),
            "res_model": "account.treasury.payment.assign",
            "view_mode": "form",
            "target": "new",
            "context": {"default_payment_id": self.id},
        }

    def action_view_treasury_forecasts(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account_treasury.account_treasury_forecast_action"
        )
        action["domain"] = [("id", "in", self.treasury_match_ids.forecast_id.ids)]
        action["context"] = {}
        return action

    def _link_treasury_forecasts_from_invoices(self):
        Match = self.env["account.treasury.match"].sudo()
        for payment in self.filtered(lambda pay: pay.state in ("in_process", "paid")):
            flow_type = "inflow" if payment.payment_type == "inbound" else "outflow"
            forecasts = payment.sudo().invoice_ids.treasury_forecast_id.filtered(
                lambda forecast, flow=flow_type, pay=payment: forecast.state
                in ("pending", "partial")
                and forecast.flow_type == flow
                and forecast.company_id == pay.company_id
            )
            for forecast in forecasts:
                values = {"forecast_id": forecast.id, "payment_id": payment.id}
                amount = Match.new(values).amount
                if not forecast.currency_id.is_zero(amount):
                    Match.create({**values, "amount": amount})
