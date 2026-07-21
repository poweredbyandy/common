{
    "name": "PBA reporte de compras / reposición",
    "version": "18.0.1.2.8",
    "category": "Inventory",
    "summary": "Reporte Excel de compras desde inventario con filtros por categoría, marca y almacén",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "stock",
        "purchase",
        "product_brand",
        "pba_internal_code",
        "pba_costs",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "wizard/purchase_replenishment_report_wizard_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": False,
}
