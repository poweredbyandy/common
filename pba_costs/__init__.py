from . import models


def post_init_hook(env):
    from .models.pba_constants import (
        DEFAULT_PBA_FINAL_COST_FORMULA,
        PREVIOUS_PBA_FINAL_COST_FORMULA,
    )

    icp = env["ir.config_parameter"].sudo()
    key = "pba_costs.final_cost_formula"
    current = (icp.get_param(key) or "").strip()
    legacy_defaults = (
        "pba_last_cost + pba_cost_fob + pba_cost_freight + pba_cost_tariff + "
        "pba_cost_operative + pba_cost_nationalization",
        PREVIOUS_PBA_FINAL_COST_FORMULA,
    )
    normalized = current.replace(" ", "")
    for old in legacy_defaults:
        if normalized == old.replace(" ", ""):
            icp.set_param(key, DEFAULT_PBA_FINAL_COST_FORMULA)
            break
