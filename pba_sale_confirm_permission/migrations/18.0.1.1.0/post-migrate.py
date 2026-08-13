from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.pba_sale_confirm_permission.hooks import (
        assign_sale_order_confirm_flag,
    )

    assign_sale_order_confirm_flag(env)
