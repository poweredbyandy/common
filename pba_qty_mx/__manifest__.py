{
    "name": "PBA cantidad en múltiplos",
    "version": "18.0.1.1.0",
    "category": "Sales",
    "summary": "Restringe la venta y facturación a cantidades múltiplo de un valor configurado en el producto.",
    "author": "andyengit",
    "maintainers": ["andyengit"],
    "license": "LGPL-3",
    "depends": [
        "product",
        "sale",
        "account",
    ],
    "data": [
        "views/product_template_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "pba_qty_mx/static/src/product_catalog/kanban_record.js",
        ],
    },
    "installable": True,
    "application": False,
}
