{
    "name": "PBA Visualización catálogo de productos",
    "version": "18.0.1.0.1",
    "category": "Sales",
    "summary": "Configura si el catálogo muestra el precio unitario y la cantidad disponible.",
    "author": "andyengit",
    "maintainers": ["andyengit"],
    "license": "LGPL-3",
    "depends": [
        "product",
        "sale",
        "stock",
    ],
    "data": [
        "views/res_config_settings_views.xml",
        "views/product_product_kanban_catalog_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "pba_product_catalog_display/static/src/js/product_catalog_display.esm.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
