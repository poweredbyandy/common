PBA_RFQ_COST_EDIT_STATES = ("draft", "sent", "to approve")

PBA_PRODUCT_COST_WRITE_FIELDS = frozenset(
    {
        "pba_cost_discount_percent",
        "pba_cost_freight_percent",
        "pba_cost_tariff_percent",
        "pba_cost_operative_percent",
        "pba_cost_nationalization_percent",
        "pba_utility_percent",
        "pba_final_cost_formula_edit",
    }
)

PBA_PURCHASE_LINE_COST_WRITE_FIELDS = frozenset(
    {
        "pba_cost_discount_percent",
        "pba_cost_freight_percent",
        "pba_cost_tariff_percent",
        "pba_cost_operative_percent",
        "pba_cost_nationalization_percent",
        "pba_utility_percent",
        "pba_sale_price_unit",
    }
)


def pba_user_can_edit_all_costs(env):
    return bool(env.su or env.user.has_group("pba_costs.group_pba_costs_edit_all"))


def pba_user_can_edit_purchase_costs(env, state):
    if pba_user_can_edit_all_costs(env):
        return True
    if env.user.has_group("pba_costs.group_pba_costs_edit_rfq"):
        return state in PBA_RFQ_COST_EDIT_STATES
    return False


DEFAULT_PBA_FINAL_COST_FORMULA = (
    "(pba_last_cost - pba_cost_discount) + pba_cost_freight + pba_cost_tariff + "
    "pba_cost_operative + pba_cost_nationalization"
)

PREVIOUS_PBA_FINAL_COST_FORMULA = (
    "pba_last_cost + pba_cost_freight + pba_cost_tariff + "
    "pba_cost_operative + pba_cost_nationalization"
)


def _pba_final_cost_formula_variable_names():
    return (
        "pba_last_cost",
        "pba_cost_discount",
        "pba_cost_discount_percent",
        "pba_cost_freight",
        "pba_cost_tariff",
        "pba_cost_operative",
        "pba_cost_nationalization",
        "pba_cost_freight_operation_total",
        "pba_cost_freight_percent",
        "pba_cost_tariff_operation_total",
        "pba_cost_tariff_percent",
        "pba_cost_operative_operation_total",
        "pba_cost_operative_percent",
        "pba_cost_nationalization_operation_total",
        "pba_cost_nationalization_percent",
        "standard_price",
        "list_price",
    )


def pba_final_cost_dummy_eval_context():
    return {k: 1.0 for k in _pba_final_cost_formula_variable_names()}
