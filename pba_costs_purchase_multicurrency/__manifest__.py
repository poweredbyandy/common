{
    "name": "PBA Costos: totales multimoneda en compras",
    "version": "18.0.1.0.1",
    "category": "Purchases",
    "summary": "Total costo final PBA en moneda del pedido y equivalencias (currency_account)",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": ["pba_costs", "purchase", "currency_account"],
    "data": ["views/purchase_order_views.xml"],
    "assets": {
        "web.assets_backend": [
            "pba_costs_purchase_multicurrency/static/src/widgets/pba_final_cost_totals_widget.xml",
            "pba_costs_purchase_multicurrency/static/src/widgets/pba_final_cost_totals_widget.js",
        ],
    },
    "installable": True,
    "application": False,
}
