{
    "name": "PBA Orden catálogo producto (Kanban)",
    "version": "18.0.1.0.5",
    "category": "Product",
    "summary": "Reordena la tarjeta kanban de productos: referencia, código, marca y nombre.",
    "description": """
        Catálogo de pedidos (product.product) y kanban de plantillas: referencia
        interna en negrita, código interno, marca, nombre destacado y el resto
        de la ficha sin cambios de estilo respecto al estándar.
    """,
    "author": "andyengit",
    "maintainers": ["andyengit"],
    "license": "LGPL-3",
    "depends": [
        "product",
        "stock",
        "pba_internal_code",
        "product_brand",
    ],
    "data": [
        "views/product_product_kanban_catalog_views.xml",
        "views/product_template_kanban_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
