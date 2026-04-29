from . import models


def post_init_hook(cr, registry):
    from odoo import api, SUPERUSER_ID

    from .models.product_template import DEFAULT_PBA_FINAL_COST_FORMULA

    env = api.Environment(cr, SUPERUSER_ID, {})
    icp = env["ir.config_parameter"].sudo()
    key = "pba_costs.final_cost_formula"
    current = (icp.get_param(key) or "").strip()
    old_default = (
        "pba_last_cost + pba_cost_fob + pba_cost_freight + pba_cost_tariff + "
        "pba_cost_operative + pba_cost_nationalization"
    )
    if current.replace(" ", "") == old_default.replace(" ", ""):
        icp.set_param(key, DEFAULT_PBA_FINAL_COST_FORMULA)
