from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.pba_skip_wizard_invoice.hooks import (
        assign_confirm_create_invoice_group,
    )

    assign_confirm_create_invoice_group(env)
