# Copyright 2026 Anderson Armeya
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, models


class ResCurrency(models.Model):
    _inherit = "res.currency"

    @api.model
    def get_exchange_rates(self):
        data = super().get_exchange_rates()
        data["spreads"] = self._get_l10n_ve_exchange_rate_spreads()
        return data

    @api.model
    def _get_l10n_ve_exchange_rate_spreads(self):
        lines = self.env["l10n.ve.currency.spread"].search(
            [("company_id", "=", self.env.company.id)]
        )
        return lines.get_spread_tooltip_data()
