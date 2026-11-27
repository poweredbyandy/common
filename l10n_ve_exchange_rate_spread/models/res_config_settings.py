# Copyright 2026 Anderson Armeya
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ve_currency_spread_ids = fields.One2many(
        related="company_id.l10n_ve_currency_spread_ids",
        readonly=False,
    )
