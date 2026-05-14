{
    "name": "PBA Ocultar costos de producto",
    "version": "18.0.1.0.0",
    "category": "Product",
    "summary": "Restringe la visibilidad del costo (standard_price) a un grupo de seguridad",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": ["product"],
    "data": [
        "security/pba_hide_costs_security.xml",
        "views/product_hide_standard_cost_views.xml",
    ],
    "installable": True,
    "application": False,
}
