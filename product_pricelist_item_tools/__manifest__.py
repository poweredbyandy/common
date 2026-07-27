{
    "name": "Product Pricelist Item Tools",
    "version": "18.0.1.0.0",
    "category": "Product",
    "summary": "Prevent duplicate products on pricelists and mass-update discount percentages",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": ["product"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/product_pricelist_item_discount_wizard_views.xml",
        "views/product_pricelist_item_views.xml",
    ],
    "installable": True,
    "application": False,
}
