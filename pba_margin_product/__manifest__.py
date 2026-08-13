{
    "name": "PBA Mrgenes Producto",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "summary": "Restringe la visibilidad de product_margin al grupo PBA: Ver mrgenes",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "pba_margin",
        "product_margin",
    ],
    "data": [
        "security/pba_margin_product_security.xml",
        "views/product_product_views.xml",
    ],
    "auto_install": True,
    "installable": True,
    "application": False,
}
