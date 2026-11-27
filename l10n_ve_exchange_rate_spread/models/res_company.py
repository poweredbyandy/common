# Copyright 2026 Anderson Armeya
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ve_currency_spread_ids = fields.One2many(
        "l10n.ve.currency.spread",
        "company_id",
        string="Comparaciones de spread",
        help="Comparaciones de tasas (desde → hacia) que se muestran en "
        "el tooltip de tasas de la barra de navegación.",
    )
