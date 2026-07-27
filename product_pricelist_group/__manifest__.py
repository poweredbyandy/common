{
    "name": "Product Pricelist Groups",
    "version": "18.0.1.4.0",
    "category": "Product",
    "summary": "Restrict pricelist visibility and usage by security groups",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": ["product", "sales_team"],
    "data": [
        "security/product_pricelist_group_security.xml",
        "views/product_pricelist_views.xml",
    ],
    "installable": True,
    "application": False,
}
