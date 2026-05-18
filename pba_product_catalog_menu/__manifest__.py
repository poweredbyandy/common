{
    "name": "PBA Menú catálogo de productos",
    "icon": "/pba_product_catalog_menu/static/description/icon.png",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "summary": "Menú principal Catálogo para consultar productos sin crear un pedido.",
    "author": "andyengit",
    "maintainers": ["andyengit"],
    "license": "LGPL-3",
    "depends": [
        "product",
        "sale",
        "stock",
        "l10n_ve_sale_product_pricelist_catalog",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/pba_product_catalog_menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "pba_product_catalog_menu/static/src/js/product_catalog_kanban_controller.js",
            "pba_product_catalog_menu/static/src/xml/product_catalog_order_line.xml",
        ],
    },
    "installable": True,
    "application": False,
}
