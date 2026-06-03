{
    "name": "PBA Backorder de proveedor",
    "version": "18.0.1.0.17",
    "summary": "Importar backorders de proveedor desde Excel como órdenes de compra",
    "category": "Inventory/Purchase",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "purchase",
        "purchase_stock",
        "pba_internal_code",
        "product_brand",
    ],
    "external_dependencies": {
        "python": ["openpyxl", "xlrd"],
    },
    "data": [
        "security/ir.model.access.csv",
        "views/purchase_order_views.xml",
        "views/product_template_views.xml",
        "wizard/supplier_backorder_import_wizard_views.xml",
        "wizard/supplier_backorder_product_wizard_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": False,
}
