{
    "name": "PBA Configurador de productos",
    "version": "18.0.1.2.0",
    "category": "Inventory/Inventory",
    "summary": (
        "Permiso para gestionar fotos de producto y del sitio web, "
        "sin crear, archivar ni eliminar productos."
    ),
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "pba_internal_code",
        "product",
        "website_sale",
    ],
    "data": [
        "security/pba_product_configurator_security.xml",
        "security/ir.model.access.csv",
        "views/product_template_views.xml",
        "views/product_configurator_menus.xml",
    ],
    "installable": True,
    "application": False,
}
