from odoo import fields, models


class PbaFinancialRiskApplyConfirmWizard(models.TransientModel):
    _name = "pba.financial.risk.apply.confirm.wizard"
    _description = "Confirmacion de actualizacion de riesgo financiero"

    settings_id = fields.Many2one(
        comodel_name="pba.financial.risk.global.settings", required=True
    )
    affected_count = fields.Integer(readonly=True)

    def action_confirm_update_all(self):
        self.ensure_one()
        return self.settings_id.with_context(
            pba_confirm_update_existing=True
        ).action_apply_global_risk_to_partners()

    def action_confirm_skip_existing(self):
        self.ensure_one()
        return self.settings_id.with_context(
            pba_skip_existing=True
        ).action_apply_global_risk_to_partners()
