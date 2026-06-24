from odoo import SUPERUSER_ID, api

from odoo.addons.poweredbyandy_e_saas.hooks import _disable_partner_autocomplete_integration


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _disable_partner_autocomplete_integration(env)
