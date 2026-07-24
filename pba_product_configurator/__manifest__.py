{
    "name": "PBA Configurador de productos",
    "version": "18.0.1.0.0",
    "category": "Inventory/Inventory",
    "summary": (
        "Permiso para crear y editar productos sin archivar ni eliminar; "
        "solo configuración de producto, sin venta ni compra."
    ),
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "product",
    ],
    "data": [
        "security/pba_product_configurator_security.xml",
        "security/ir.model.access.csv",
        "views/product_configurator_menus.xml",
    ],
    "installable": True,
    "application": False,
}
