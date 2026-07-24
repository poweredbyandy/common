{
    "name": "PBA Configurador de productos",
    "version": "18.0.1.3.2",
    "category": "Inventory/Inventory",
    "summary": (
        "Permiso para gestionar fotos de producto y del sitio web; "
        "solo ve productos, sin Contactos ni otras apps."
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
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
