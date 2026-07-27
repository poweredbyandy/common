{
    "name": "PBA Custom Seller",
    "version": "18.0.1.2.0",
    "category": "Sales",
    "summary": "Limited seller: own contacts, products from pricelists, optional stock qty and SO confirm",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
        "sale_stock",
        "stock",
        "product_pricelist_group",
    ],
    "data": [
        "security/pba_custom_seller_security.xml",
        "views/product_views.xml",
        "views/sale_order_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
