from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["product.template"].pba_recompute_cost_amounts_from_last_cost()
