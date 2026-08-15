{
    "name": "Product Change",
    "version": "18.0.1.0.0",
    "category": "Inventory/Inventory",
    "summary": "Change product type, quantity tracking and unit of measure",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": ["sale_stock", "purchase_stock"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/product_change_wizard_views.xml",
        "views/product_template_views.xml",
    ],
    "installable": True,
    "application": False,
}
