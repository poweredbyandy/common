{
    "name": "PBA Devolucion desde nota de credito",
    "version": "18.0.1.0.4",
    "category": "Sales/Sales",
    "summary": "Crea un albaran de devolucion al confirmar una nota de credito "
    "y ajusta la cantidad pedida del pedido al validar la devolucion.",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": ["sale_stock"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/res_company_views.xml",
        "views/account_move_views.xml",
        "views/stock_picking_views.xml",
    ],
    "pre_init_hook": "pre_init_hook",
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
