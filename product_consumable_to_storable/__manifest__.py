{
    "name": "Product Consumable to Storable",
    "version": "18.0.1.0.0",
    "category": "Inventory/Inventory",
    "summary": "Convert consumable products to quantity-tracked inventory and rebuild stock",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": ["stock"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/product_consumable_to_storable_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}
