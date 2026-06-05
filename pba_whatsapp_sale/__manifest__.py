{
    "name": "PBA WhatsApp Ventas",
    "version": "18.0.1.0.9",
    "category": "Sales",
    "summary": "Plantillas y envío WhatsApp para presupuestos, pedidos y entregas",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": ["pba_whatsapp", "sale", "sale_stock"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/sale_order_views.xml",
        "views/stock_picking_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
